import itertools

import crypto
import bls
import vss


def test_signing():
    sk, bls_pk = bls.keygen()
    msg = 'test message'
    sig = bls.sign(sk, msg)
    assert bls.verify(bls_pk, msg, sig)


def test_signature_aggregation():
    n = 5
    t = 3

    sk, bls_pk = bls.keygen()
    msg = 'test message'
    sig = bls.sign(sk, msg)

    sk_shares, _ = vss.share(sk, n, t)
    partial_sigs = [bls.sign(partial_sk, msg) for partial_sk in sk_shares]
    indexed_partial_sigs = [(i, sig) for i, sig in zip(range(1, n + 1), partial_sigs)]

    for selected_partial_sigs in itertools.combinations(indexed_partial_sigs, t):
        aggregated_sig = vss.recover_point(selected_partial_sigs)
        assert sig == aggregated_sig


def test_all_to_all_signature_aggregation():
    n = 5
    t = 3

    sks = [crypto.random_scalar() for _ in range(n)]
    master_sk = sum(sks) % crypto.CURVE_ORDER
    msg = 'test message'
    sig = bls.sign(master_sk, msg)

    agg_sks = [0] * n
    for sk in sks:
        sk_shares, _ = vss.share(sk, n, t)
        for i, sk_share in enumerate(sk_shares):
            agg_sks[i] += sk_share

    partial_sigs = [bls.sign(psk, msg) for psk in agg_sks]
    indexed_partial_sigs = [(i, sig) for i, sig in zip(range(1, n + 1), partial_sigs)]

    for selected_partial_sigs in itertools.combinations(indexed_partial_sigs, t):
        aggregated_sig = vss.recover_point(selected_partial_sigs)
        assert sig == aggregated_sig
