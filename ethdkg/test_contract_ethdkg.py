import pytest

from typing import List, Tuple

from . import utils
from .utils import STATUS_OK, STATUS_ERROR
from .node import INVALID_SHARE
from .ethnode import EthNode, point_to_eth, point_G2_to_eth
from .crypto import G1, H1, G2, H2, multiply, neg

from .utils import (
    mine_until_registrations_confirmed,
    mine_until_share_distribution_confirmed,
    mine_until_disputes_confirmed,
    mine_until_key_share_submission_confirmed,
)

DUMMY_PK = [1, 2]
DUMMY_SHARE = [4711]
DUMMY_COMMITMENT = [1, 2]


@pytest.fixture(scope="session", autouse=True)
def compile_contract(request):
    utils.compile_contract("ETHDKG")


@pytest.fixture()
def contract():
    return utils.deploy_contract("ETHDKG")


def init_scenario(contract, n=5, t=2) -> Tuple[int, int, List[EthNode]]:
    nodes = [EthNode(utils.get_account_address(i), contract) for i in range(n)]
    return n, t, nodes


def test_compilation():
    utils.compile_contract("ETHDKG")


def test_deployment(contract):
    # tests fixture for contract
    pass


def test_bn128_check_pairing(contract):
    assert contract.caller.bn128_check_pairing(
        [
            *point_to_eth(multiply(G1, 5771)),
            *point_G2_to_eth(neg(G2)),
            *point_to_eth(G1),
            *point_G2_to_eth(multiply(G2, 5771)),
        ]
    )


def test_register(contract):
    tx_receipt = contract.register(DUMMY_PK).call_sync()
    assert tx_receipt.status == STATUS_OK
    return contract, tx_receipt


def test_register__too_late(contract):
    utils.mine_blocks_until(lambda: utils.block_number() > contract.caller.T_REGISTRATION_END())
    tx_receipt = contract.register(DUMMY_PK).call_sync()
    assert tx_receipt.status == STATUS_ERROR
    return contract, tx_receipt


def test_register__twice(contract):
    tx_receipt = contract.register(DUMMY_PK).call_sync()
    assert tx_receipt.status == STATUS_OK
    tx_receipt = contract.register(DUMMY_PK).call_sync()
    assert tx_receipt.status == STATUS_ERROR
    return contract, tx_receipt


def test_register__invalid_pk(contract):
    tx_receipt = contract.register([1, 3]).call_sync()
    # the point (1, 3) is not on the elliptic curve
    # consequently the registration process should fail
    assert tx_receipt.status == STATUS_ERROR


def test_setup(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()

    mine_until_registrations_confirmed(contract)
    assert contract.caller.num_nodes() == n

    for node in nodes:
        node.setup()

    return contract, nodes


def test_share_distribution(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    for node in nodes:
        node.setup()
        node.distribute_shares()
    mine_until_share_distribution_confirmed(contract)

    for node in nodes:
        assert contract.caller.share_distribution_hashes(node.address) != bytes(32)
    for node in nodes:
        node.load_shares()
    return contract, nodes


def distribute_invalid_shares(issuer, receiver):
    encrypted_shares, commitments = issuer.compute_shares()
    encrypted_shares[receiver.idx] += 1
    encrypted_shares = list(encrypted_shares.values())
    commitments = [point_to_eth(c) for c in commitments]
    issuer.contract.distribute_shares(encrypted_shares, commitments).call_async(issuer.address)


def distribute_invalid_commitment(issuer):
    encrypted_shares, commitments = issuer.compute_shares()
    encrypted_shares = list(encrypted_shares.values())
    commitments = [point_to_eth(c) for c in commitments]
    commitments[0] = (1, 3)
    return issuer.contract.distribute_shares(encrypted_shares, commitments).call_sync(
        issuer.address
    )


def test_share_distribution__invalid_commitment(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    nodes[0].setup()
    tx_receipt = distribute_invalid_commitment(nodes[0])

    assert tx_receipt.status == STATUS_ERROR


def test_dispute__invalid_share(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    for node in nodes:
        node.setup()

    for node in nodes:
        if node is nodes[0]:
            distribute_invalid_shares(issuer=nodes[0], receiver=nodes[1])
        else:
            node.distribute_shares()
    mine_until_share_distribution_confirmed(contract)

    for node in nodes:
        node.load_shares()

    assert nodes[1].decrypted_shares[nodes[0].idx] == INVALID_SHARE

    tx_dispute_receipts = nodes[1].submit_disputes(sync=True)
    assert len(tx_dispute_receipts) == 1
    for tx_receipt in tx_dispute_receipts.values():
        assert tx_receipt.status == STATUS_OK

    mine_until_disputes_confirmed(contract)
    for node in nodes:
        node.load_disputes()
        assert node.disputed_nodes == {nodes[0].idx}

    return contract, nodes


def test_dispute__valid_share(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    for node in nodes:
        node.setup()
        node.distribute_shares()
    mine_until_share_distribution_confirmed(contract)

    for node in nodes:
        node.load_shares()

    # mark share as invalid alltough it is not
    nodes[1].decrypted_shares[nodes[0].idx] = INVALID_SHARE

    tx_dispute_receipts = nodes[1].submit_disputes(sync=True)
    assert len(tx_dispute_receipts) == 1
    for tx_receipt in tx_dispute_receipts.values():
        assert tx_receipt.status == STATUS_ERROR


def test_submit_key_share(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    for node in nodes:
        node.setup()
        node.distribute_shares()
    mine_until_share_distribution_confirmed(contract)

    for node in nodes:
        node.load_shares()
        node.submit_disputes()
    mine_until_disputes_confirmed(contract)

    for node in nodes:
        node.load_disputes()
        node.compute_qualified_nodes()
        tx_receipt = node.submit_key_share(sync=True)
        assert tx_receipt.status == STATUS_OK
    mine_until_key_share_submission_confirmed(contract)

    for node in nodes:
        node.load_key_shares()
        assert len(node.key_shares) == n

    return contract, nodes


def test_submit_key_share__recovery(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    for node in nodes:
        node.setup()
        node.distribute_shares()
    mine_until_share_distribution_confirmed(contract)

    for node in nodes:
        node.load_shares()
        node.submit_disputes()
    mine_until_disputes_confirmed(contract)

    for node in nodes:
        node.load_disputes()
        node.compute_qualified_nodes()
        if node is not nodes[0]:
            node.submit_key_share()
    mine_until_key_share_submission_confirmed(contract)

    assert contract.caller.key_shares(nodes[0].address, 0) == 0

    for node in nodes:
        node.load_key_shares()
        assert len(node.key_shares) == n - 1
        if node is not nodes[0]:
            node.recover_key_shares()

    utils.mine_block()
    for node in nodes:
        node.load_recovered_key_shares()

    for node in nodes:
        tx_receipts = node.submit_recovered_key_shares(sync=True)
        for tx_receipt in tx_receipts.values():
            assert tx_receipt.status == STATUS_OK

    assert contract.caller.key_shares(nodes[0].address, 0) != 0
    return contract, nodes


def test_key_derivation(contract):
    n, t, nodes = init_scenario(contract)

    for node in nodes:
        node.register()
    mine_until_registrations_confirmed(contract)

    for node in nodes:
        node.setup()
        node.distribute_shares()
    mine_until_share_distribution_confirmed(contract)

    for node in nodes:
        node.load_shares()
        node.submit_disputes()
    mine_until_disputes_confirmed(contract)

    for node in nodes:
        node.load_disputes()
        node.compute_qualified_nodes()
        node.submit_key_share()
    mine_until_key_share_submission_confirmed(contract)

    for node in nodes:
        node.load_key_shares()

    for node in nodes:
        node.load_key_shares()
        tx_receipt = node.submit_master_public_key(sync=True)
        assert tx_receipt.status == STATUS_OK
        node.derive_group_keys()
