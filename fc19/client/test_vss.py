import itertools

import vss
from crypto import G1, random_scalar, multiply


def test_sharing():
    n = 5
    t = 3
    secret = random_scalar()
    shares, _ = vss.share(secret, n, t)
    indexed_shares = list(zip(range(1, n + 1), shares))

    for selected_shares in itertools.combinations(indexed_shares, t):
        recovered_secret = vss.recover(indexed_shares)
        assert secret == recovered_secret


def test_verification():
    n = 5
    t = 3
    secret = random_scalar()
    shares, public_coefficients = vss.share(secret, n, t)
    for id, share in zip(range(1, n + 1), shares):
        assert vss.verify(id, share, public_coefficients)


def test_dleq():
    sk1 = random_scalar(seed=1)
    sk2 = random_scalar(seed=2)
    pk1 = multiply(G1, sk1)
    pk2 = multiply(G1, sk2)

    shared_key = multiply(pk2, sk1)
    assert shared_key == multiply(pk1, sk2)

    challenge, response = vss.dleq(G1, pk1, pk2, shared_key, alpha=sk1)
    assert vss.dleq_verify(G1, pk1, pk2, shared_key, challenge, response)

    response += 1
    assert not vss.dleq_verify(G1, pk1, pk2, shared_key, challenge, response)


def test_sk_knowledge():
    sk = random_scalar()
    pk = multiply(G1, sk)
    challenge, response = vss.prove_sk_knowledge(sk, pk)
    assert vss.verify_sk_knowledge(pk, challenge, response)


def test_sk_knowledge_with_account():
    sk = random_scalar()
    pk = multiply(G1, sk)
    challenge, response = vss.prove_sk_knowledge(sk, pk, account="0xe3D320ea4AF151Fc309568884C217f634E9c38f5")
    assert vss.verify_sk_knowledge(pk, challenge, response, account="0xe3D320ea4AF151Fc309568884C217f634E9c38f5")


def test_sk_knowledge_invalid_pk():
    sk = random_scalar()
    pk = multiply(G1, sk + 1)
    challenge, response = vss.prove_sk_knowledge(sk, pk)
    assert not vss.verify_sk_knowledge(pk, challenge, response)


def test_sk_knowledge_invalid_response():
    sk = random_scalar()
    pk = multiply(G1, sk)
    challenge, response = vss.prove_sk_knowledge(sk, pk)
    response += 1
    assert not vss.verify_sk_knowledge(pk, challenge, response)
