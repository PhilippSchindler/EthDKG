import pytest

import utils
import crypto
import vss

from node import Node
from ethnode import EthNode
from constants import *

w3 = utils.connect()
account = w3.eth.accounts[-1]


def setup_single():
    contract = utils.deploy_contract('DKG')
    node = EthNode(account)
    node.keygen()
    node.connect(contract)
    return node, contract


def setup_multiple(num_nodes=3, register=False):
    assert num_nodes <= len(w3.eth.accounts), \
        "Each node needs a seperate account, update e.g. Ganache settings for more accounts"

    contract = utils.deploy_contract('DKG')
    nodes = [EthNode(w3.eth.accounts[i]) for i in range(num_nodes)]
    for node in nodes:
        c = utils.get_contract('DKG', contract.address)
        node.keygen()
        node.connect(c)

    if register:
        utils.run([node.register for node in nodes])
        utils.mine_blocks_until(contract.registrations_confirmed)
        utils.run([node.init_secret_sharing for node in nodes])

        # here we actually ensure that we return the nodes ordered by id, for easier tests
        nodes.sort(key=lambda node: node.id)

    return contract, nodes


def test_registration():
    node, contract = setup_single()
    node.register()
    events = utils.get_events(contract, EVENT_REGISTRATION)
    assert len(events) == 1


def test_registration_prohibt_multiple_attemps():
    node, contract = setup_single()
    node.register()
    with pytest.raises(ValueError, match='.*registration failed.*'):
        node.register()
    events = utils.get_events(contract, EVENT_REGISTRATION)
    assert len(events) == 1


def test_registration_prohibt_late_submission():
    node, contract = setup_single()
    utils.mine_blocks_until(lambda: not contract.in_registration_phase())

    with pytest.raises(AssertionError):
        node.register()
    with pytest.raises(ValueError, match='.*registration failed.*'):
        node.register(check_contract_phase=False)
    events = utils.get_events(contract, EVENT_REGISTRATION)
    assert len(events) == 0


def test_registration_invalid_pk():
    """ nodes tries to register with some public key which is not a valid point on the curve
    """
    node, contract = setup_single()

    x, y = node.pk
    while True:
        x += 1
        if not crypto.is_on_curve((x, y)):
            break
    node.pk = (x, y)

    with pytest.raises(ValueError, match='.*elliptic curve pairing failed*'):
        node.register()


def test_registration_invalid_bls_pk():
    node, contract = setup_single()
    # use invalid (e.g. some other) bls_pk
    # as it does not match the stored pk, the registration should fail
    other_node = Node()
    other_node.keygen()
    node.bls_pk = other_node.bls_pk
    with pytest.raises(ValueError, match='.*registration failed.*'):
        node.register()


def test_registration_invalid_sk_knowledge_proof():
    contract, nodes = setup_multiple(num_nodes=2, register=False)
    A, B = nodes
    invalid_sk_knowledge_proof = vss.prove_sk_knowledge(B.sk, B.pk, A.account)
    with pytest.raises(ValueError, match='.*registration failed.*'):
        contract.register(A.pk, A.bls_pk, invalid_sk_knowledge_proof, transact={'from': A.account})


def test_init_secret_sharing():
    contract, nodes = setup_multiple()

    utils.run([node.register for node in nodes])
    utils.mine_blocks_until(contract.registrations_confirmed)

    utils.run([node.init_secret_sharing for node in nodes])

    for node in nodes:
        assert len(node.nodes) == len(nodes)

    # in the following we will use the shorthand setup_multiple(register=True) for the above code


def test_sharing():
    contract, nodes = setup_multiple(register=True)

    utils.run([node.share_key for node in nodes])

    events = utils.get_events(contract, EVENT_KEY_SHARING)
    assert len(events) == len(nodes)


def test_sharing_early():
    contract, nodes = setup_multiple()

    utils.run([node.register for node in nodes])
    nodes[0].init_secret_sharing(check_contract_phase=False)

    with pytest.raises(ValueError, match='.*key sharing failed.*'):
        nodes[0].share_key(check_contract_phase=False)


def test_sharing_late():
    contract, nodes = setup_multiple(register=True)

    utils.run([node.share_key for node in nodes[1:]])
    utils.mine_blocks_until(lambda: not contract.in_sharing_phase())

    with pytest.raises(ValueError, match='.*key sharing failed.*'):
        nodes[0].share_key()


def test_sharing_non_registered():

    contractA, nodes = setup_multiple(6)
    contractB = utils.deploy_contract('DKG')

    nodesA = nodes[:3]
    nodesB = nodes[3:]
    for b in nodesB:
        b.contract = contractB

    utils.run([node.register for node in nodesA])
    utils.run([node.register for node in nodesB])
    utils.mine_blocks_until(contractA.registrations_confirmed)
    utils.mine_blocks_until(contractB.registrations_confirmed)

    utils.run([node.init_secret_sharing for node in nodesA])
    utils.run([node.init_secret_sharing for node in nodesB])

    bad_node = nodesB[0]
    bad_node.contract = contractA

    with pytest.raises(ValueError, match='.*key sharing failed.*'):
        # bad_node is not registered for contract A, call to contract should therefore fail
        bad_node.share_key()


def test_verification_of_valid_shares(test_dispute=True):
    contract, nodes = setup_multiple(register=True)

    utils.run([node.share_key for node in nodes])
    utils.mine_blocks_until(contract.sharing_confirmed)

    # as everything is valid, no node should raise an exception during loading of the shares
    for node in nodes:
        node.load_shares()

    if test_dispute:
        with pytest.raises(ValueError, match='.*dispute failed.*share was valid.*'):
            nodes[0].dispute(issuer_id=nodes[-1].id)


def test_verification_of_invalid_shares(test_dispute=True):
    contract, nodes = setup_multiple(3, register=True)
    issuer, verifier = nodes[0], nodes[2]

    share = issuer.shares[verifier.id - 1]
    invalid_share = share + 1
    invalid_encrypted_share = vss.encrypt_share(invalid_share, verifier.id, vss.shared_key(issuer.sk, verifier.pk))
    issuer.encrypted_shares[-1] = invalid_encrypted_share

    utils.run([node.share_key for node in nodes])
    utils.mine_blocks_until(contract.sharing_confirmed)

    with pytest.raises(ValueError):
        verifier.load_shares()

    # dispute should succeed and not raise any error
    if test_dispute:
        verifier.dispute(issuer_id=issuer.id)


def test_verification_invalid_encryption_key(test_dispute=True):
    contract, nodes = setup_multiple(3, register=True)
    issuer, verifier = nodes[0], nodes[2]
    other_node = Node()
    other_node.keygen()

    share = issuer.shares[verifier.id - 1]
    invalid_shared_key = vss.shared_key(issuer.sk, other_node.pk)
    invalid_encrypted_share = vss.encrypt_share(share, verifier.id, invalid_shared_key)
    issuer.encrypted_shares[-1] = invalid_encrypted_share

    utils.run([node.share_key for node in nodes])
    utils.mine_blocks_until(contract.sharing_confirmed)

    with pytest.raises(ValueError):
        verifier.load_shares()

    # dispute should succeed and not raise any error
    if test_dispute:
        verifier.dispute(issuer_id=nodes[0].id)


def test_verification_invalid_public_coefficients(test_dispute=True):
    contract, nodes = setup_multiple(3, register=True)
    issuer, verifier = nodes[0], nodes[2]

    # invalidate first public coefficient
    C1x, C1y = issuer.public_coefficients[0]
    issuer.public_coefficients[0] = (C1x + 1, C1y)

    utils.run([node.share_key for node in nodes])
    utils.mine_blocks_until(contract.sharing_confirmed)

    with pytest.raises(ValueError):
        verifier.load_shares()

    # dispute should succeed and not raise any error
    if test_dispute:
        verifier.dispute(issuer_id=nodes[0].id)


def test_upload_group_key():
    contract, nodes = setup_multiple(3, register=True)

    utils.run([node.share_key for node in nodes])
    utils.mine_blocks_until(contract.sharing_confirmed)

    utils.run([node.load_shares() for node in nodes])
    utils.mine_blocks_until(contract.dispute_confirmed)

    nodes[0].derive_group_keys()

    assert crypto.check_pairing(
        nodes[0].master_pk, crypto.G2,
        crypto.G1, nodes[0].master_bls_pk,
    )

    nodes[0].upload_group_key()
