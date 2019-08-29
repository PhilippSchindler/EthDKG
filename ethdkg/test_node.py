import pytest
import random

from typing import Tuple, List, Dict, Optional, Set

from .node import Node, INVALID_SHARE
from .crypto import normalize, add, multiply, G1, H1, G2, H2
from . import crypto


def init_scenario(
    n: int = 5, t: int = 2, use_random_indices: bool = True
) -> Tuple[int, int, List[Node]]:
    nodes = [Node() for _ in range(n)]

    indices = list(range(1, n + 1))
    if use_random_indices:
        indices = random.sample(range(1, 10000), n)

    public_keys = {idx: node.public_key for idx, node in zip(indices, nodes)}

    for idx, node in zip(indices, nodes):
        node.setup(n, t, idx, public_keys)

    return n, t, nodes


def compute_and_distribute_shares(
    nodes: List[Node],
    invalid_shares_from_to: Optional[Set[Tuple[Node, Node]]] = None,
    invalid_commitments_from: Optional[Set[Node]] = None,
    do_not_distribute_from: Optional[Set[Node]] = None,
):
    invalid_shares_from_to = invalid_shares_from_to or set()
    invalid_commitments_from = invalid_commitments_from or set()
    do_not_distribute_from = do_not_distribute_from or set()

    all_encrypted_shares = {}
    all_commitments = {}
    for node in nodes:
        all_encrypted_shares[node.idx], all_commitments[node.idx] = node.compute_shares()

    for issuer in nodes:
        if issuer in invalid_commitments_from:
            all_commitments[issuer.idx][0] = multiply(all_commitments[issuer.idx][0], 2)
        for receiver in nodes:
            if (issuer, receiver) in invalid_shares_from_to:
                assert issuer.idx != receiver.idx, "error in testcase"
                all_encrypted_shares[issuer.idx][receiver.idx] += 1

    for issuer in nodes:
        if issuer in do_not_distribute_from:
            continue
        for receiver in nodes:
            if issuer.idx == receiver.idx:
                continue
            ok = receiver.load_shares(
                issuer.idx, all_encrypted_shares[issuer.idx], all_commitments[issuer.idx]
            )
            if (issuer, receiver) in invalid_shares_from_to or issuer in invalid_commitments_from:
                assert not ok, "invalid share should be detected"
            else:
                assert ok, "verification should pass, since the share is valid"


def test_shared_keys():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    assert normalize(n1.shared_keys[n2.idx]) == normalize(n2.shared_keys[n1.idx])


def test_share_distribution_all_fine_case():
    n, t, nodes = init_scenario()
    compute_and_distribute_shares(nodes)


def test_share_distribution_node_invalid_shares_should_be_detected():
    n, t, nodes = init_scenario()
    n1, n2, n3, *_ = nodes
    compute_and_distribute_shares(nodes, invalid_shares_from_to={(n1, n2), (n1, n3), (n3, n1)})


def test_share_distribution_node_invalid_commitments_should_be_detected():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes, invalid_commitments_from={n1, n2})


def compute_and_distribute_disputes(nodes):
    all_disputes = {node.idx: node.compute_disputes() for node in nodes}
    for node in nodes:
        for disputer_idx, disputes in all_disputes.items():
            for issuer_idx, dispute in disputes.items():
                assert node.load_dispute(issuer_idx, disputer_idx, *dispute)


def test_valid_dispute_accepted():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes, invalid_shares_from_to={(n1, n2)})

    disputes = n2.compute_disputes()
    assert len(disputes) == 1
    for node in nodes:
        assert node is n2 or len(node.compute_disputes()) == 0

    dispute = disputes[n1.idx]
    for node in nodes:
        assert node.load_dispute(n1.idx, n2.idx, *dispute)


def test_invalid_dispute_rejected__invalid_key():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes, invalid_shares_from_to={(n1, n2)})

    dispute = n2.compute_disputes()[n1.idx]
    shared_key, proof = dispute
    shared_key = multiply(shared_key, 4711)

    for node in nodes:
        assert not node.load_dispute(n1.idx, n2.idx, shared_key, proof)


def test_invalid_dispute_rejected__invalid_key_proof():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes, invalid_shares_from_to={(n1, n2)})

    dispute = n2.compute_disputes()[n1.idx]
    shared_key, proof = dispute
    proof = proof[0], proof[1] + 4711

    for node in nodes:
        assert not node.load_dispute(n1.idx, n2.idx, shared_key, proof)


def test_invalid_dispute_rejected__share_valid():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes)

    # wrongly mark share as invalid so that the node actually creates a dispute
    n2.decrypted_shares[n1.idx] = INVALID_SHARE

    dispute = n2.compute_disputes()[n1.idx]
    for node in nodes:
        assert not node.load_dispute(n1.idx, n2.idx, *dispute)


def test_qualified_nodes__all():
    n, t, nodes = init_scenario()
    compute_and_distribute_shares(nodes)
    compute_and_distribute_disputes(nodes)

    for node in nodes:
        assert node.compute_qualified_nodes() == [node.idx for node in nodes]


def test_qualified_nodes__exclude_disputed():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes, invalid_shares_from_to={(n1, n2)})
    compute_and_distribute_disputes(nodes)

    qualified_nodes = [node.idx for node in nodes if node is not n1]
    for node in nodes:
        assert node.compute_qualified_nodes() == qualified_nodes


def test_qualified_nodes__exclude_undistributed():
    n, t, nodes = init_scenario()
    n1, *_ = nodes
    compute_and_distribute_shares(nodes, do_not_distribute_from={n1})
    compute_and_distribute_disputes(nodes)

    qualified_nodes = [node.idx for node in nodes if node is not n1]
    for node in nodes:
        if node is not n1:
            assert node.compute_qualified_nodes() == qualified_nodes


def compute_and_distribute_key_shares(nodes):
    for node in nodes:
        node.compute_qualified_nodes()
    all_key_shares = {node.idx: node.compute_key_share() for node in nodes}
    for receiving_node in nodes:
        for issuer_idx, key_shares in all_key_shares.items():
            assert receiving_node.load_key_share(issuer_idx, *key_shares)


def test_key_shares_verification__all_correct():
    n, t, nodes = init_scenario()
    compute_and_distribute_shares(nodes)
    compute_and_distribute_disputes(nodes)
    compute_and_distribute_key_shares(nodes)


def test_key_shares_verification__invalid():
    n, t, nodes = init_scenario()
    compute_and_distribute_shares(nodes)
    compute_and_distribute_disputes(nodes)
    for node in nodes:
        node.compute_qualified_nodes()
        node.compute_key_share()

    n1, n2, *_ = nodes

    h1 = multiply(H1, n1.secret)
    h1_proof = crypto.dleq(H1, h1, G1, n1.commitments[n1.idx][0], n1.secret)
    h2 = multiply(H2, n1.secret)
    assert n2.load_key_share(n1.idx, h1, h1_proof, h2)

    h1 = multiply(H1, n1.secret)
    h1_proof = crypto.dleq(
        multiply(H1, 2), h1, multiply(G1, 2), n1.commitments[n1.idx][0], n1.secret
    )
    h2 = multiply(H2, n1.secret)
    assert not n2.load_key_share(n1.idx, h1, h1_proof, h2)

    h1 = multiply(H1, n1.secret + 1)
    h1_proof = crypto.dleq(H1, h1, G1, n1.commitments[n1.idx][0], n1.secret)
    h2 = multiply(H2, n1.secret + 1)
    assert not n2.load_key_share(n1.idx, h1, h1_proof, h2)

    h1 = multiply(H1, n1.secret)
    h1_proof = crypto.dleq(H1, h1, G1, n1.commitments[n1.idx][0], n1.secret)
    h2 = multiply(H2, n1.secret + 1)
    assert not n2.load_key_share(n1.idx, h1, h1_proof, h2)


def test_key_shares_recovery():
    n, t, nodes = init_scenario()
    n1, n2, *_ = nodes
    compute_and_distribute_shares(nodes)
    compute_and_distribute_disputes(nodes)
    compute_and_distribute_key_shares(nodes)

    recs_for_n1 = {
        node.idx: node.initiate_key_share_recovery(n1.idx) for node in nodes if node is not n1
    }

    for verifier in nodes:
        if verifier is n1:
            continue
        for recoverer_idx, rec in recs_for_n1.items():
            assert verifier.load_recovered_key_share(n1.idx, recoverer_idx, *rec)

    for verifier in nodes:
        if verifier is n1:
            continue
        x = verifier.key_shares
        assert verifier.recover_key_share(n1.idx)
        assert x == verifier.key_shares


def test_master_key_derivation():
    n, t, nodes = init_scenario()
    n1, *_ = nodes
    compute_and_distribute_shares(nodes)
    compute_and_distribute_disputes(nodes)
    compute_and_distribute_key_shares(nodes)

    for node in nodes:
        node.derive_master_public_key()

    mk = normalize(n1.master_public_key)
    for node in nodes:
        assert mk == normalize(node.master_public_key)


def test_group_key_derivation():
    n, t, nodes = init_scenario()
    n1, *_ = nodes
    compute_and_distribute_shares(nodes)
    compute_and_distribute_disputes(nodes)
    compute_and_distribute_key_shares(nodes)

    for node in nodes:
        node.derive_group_keys()

    for node in nodes:
        assert n1.verify_group_public_key(
            node.idx,
            node.group_public_key,
            node.group_public_key_in_G1,
            node.group_public_key_correctness_proof,
        )

