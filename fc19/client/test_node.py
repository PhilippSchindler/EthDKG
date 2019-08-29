import pytest
import itertools

import crypto
import bls
import vss

from node import Node


def setup_and_register(n=3):
    nodes = [Node(id=i) for i in range(1, n + 1)]
    for node in nodes:
        node.keygen()
    infos = [node.registration_info() for node in nodes]
    for node in nodes:
        node.init_secret_sharing(infos)
    return nodes


def test_load_valid_shares():
    nodes = setup_and_register()
    for receiver, issuer in itertools.product(nodes, repeat=2):
        if receiver != issuer:
            receiver.load_shares(issuer.id, issuer.encrypted_shares, issuer.public_coefficients)


def test_load_invalid_shares():
    nodes = setup_and_register()
    bad_node = nodes[0]
    bad_node.encrypted_shares = [
        vss.encrypt_share(share + 1, receiver.id, vss.shared_key(bad_node.sk, receiver.pk))
        for share, receiver in zip(bad_node.shares[1:], nodes[1:])
    ]
    for receiver in nodes[1:]:
        with pytest.raises(ValueError):
            receiver.load_shares(bad_node.id, bad_node.encrypted_shares, bad_node.public_coefficients)


def test_load_invalid_shares_wrong_encryption_key_used():
    nodes = setup_and_register()
    invalid_encryption_key = crypto.G1
    bad_node = nodes[0]
    bad_node.encrypted_shares = [
        vss.encrypt_share(share, receiver.id, invalid_encryption_key)
        for share, receiver in zip(bad_node.shares[1:], nodes[1:])
    ]
    for receiver in nodes[1:]:
        with pytest.raises(ValueError):
            receiver.load_shares(bad_node.id, bad_node.encrypted_shares, bad_node.public_coefficients)


def test_load_invalid_shares_public_coefficients_wrong():
    nodes = setup_and_register()

    dummy_node = Node(id=1)
    dummy_node.keygen()
    dummy_node.init_secret_sharing([node.registration_info() for node in [dummy_node] + nodes[1:]])

    bad_node = nodes[0]
    bad_node.public_coefficients[0] = dummy_node.public_coefficients[0]

    for receiver in nodes[1:]:
        with pytest.raises(ValueError):
            receiver.load_shares(bad_node.id, bad_node.encrypted_shares, bad_node.public_coefficients)


def test_load_valid_shares_pk_wrong():
    nodes = setup_and_register()

    dummy_node = Node(id=1)
    dummy_node.keygen()

    bad_node = nodes[0]
    bad_node.sk = dummy_node.sk
    bad_node.pk = dummy_node.pk
    bad_node.bls_pk = dummy_node.bls_pk

    infos = [node.registration_info() for node in nodes]
    bad_node.init_secret_sharing(infos)

    for receiver in nodes[1:]:
        with pytest.raises(ValueError):
            receiver.load_shares(bad_node.id, bad_node.encrypted_shares, bad_node.public_coefficients)


def test_derive_group_key():
    nodes = setup_and_register()
    for receiver, issuer in itertools.product(nodes, repeat=2):
        if receiver != issuer:
            receiver.load_shares(issuer.id, issuer.encrypted_shares, issuer.public_coefficients)

    for node in nodes:
        node.load_dispute_infos(disputed_node_ids=set())
        node.derive_group_keys()

    master_pk = nodes[0].master_pk
    master_bls_pk = nodes[0].master_bls_pk
    for node in nodes[1:]:
        assert master_pk == node.master_pk
        assert master_bls_pk == node.master_bls_pk


def test_derive_group_key_with_dispute():
    nodes = setup_and_register()
    for receiver, issuer in itertools.product(nodes, repeat=2):
        if receiver != issuer:
            receiver.load_shares(issuer.id, issuer.encrypted_shares, issuer.public_coefficients)

    for node in nodes:
        node.load_dispute_infos(disputed_node_ids={1})
        node.derive_group_keys()

    master_pk = nodes[1].master_pk
    master_bls_pk = nodes[1].master_bls_pk
    for node in nodes[2:]:
        assert master_pk == node.master_pk
        assert master_bls_pk == node.master_bls_pk


def test_group_signature():
    nodes = setup_and_register(n=3)
    for receiver, issuer in itertools.product(nodes, repeat=2):
        if receiver != issuer:
            receiver.load_shares(issuer.id, issuer.encrypted_shares, issuer.public_coefficients)

    for node in nodes:
        node.load_dispute_infos(disputed_node_ids={1})
        node.derive_group_keys()

    master_bls_pk = nodes[1].master_bls_pk
    msg = 'test group signing'

    partial_sigs = [(node.id, node.sign(msg)) for node in nodes]
    group_sig = bls.aggregate(partial_sigs[1:])       # only use the last t signatures
    assert bls.verify(master_bls_pk, msg, group_sig)


# def test_verification_invalid_public_coefficients(test_dispute=True):
#     contract, nodes = setup_multiple(3, register=True)
#     issuer, verifier = nodes[0], nodes[2]

#     # invalidate first public coefficient
#     C1x, C1y = issuer.public_coefficients[0]
#     issuer.public_coefficients[0] = (C1x + 1, C1y)

#     utils.run([node.share_key for node in nodes])
#     utils.mine_blocks_until(contract.sharing_confirmed)

#     with pytest.raises(ValueError):
#         verifier.load_shares()

#     # dispute should succeed and not raise any error
#     if test_dispute:
#         verifier.dispute(issuer_id=nodes[0].id)


# contract testcases
#  - upload invalid public key
#  - upload wrong bls public key
#  - upload invalid bls public key
#  - public key duplication attack on registration

# special issues
