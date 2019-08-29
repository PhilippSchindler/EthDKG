import pytest
import random

from collections import defaultdict

from .crypto import G1, G2, H1, H2
from .crypto import add, multiply, normalize, pairing
from .crypto import random_scalar, keygen
from .crypto import share_secret, verify_share, recover_secret
from .crypto import shared_key, encrypt_share, decrypt_share
from .crypto import dleq, dleq_verify
from .crypto import sum_scalars, sum_points
from .crypto import evaluate_public_polynomial


def test_keygen():
    sk, pk = keygen()
    assert sk is not None
    assert pk is not None


def test_share_secret():
    n = 10
    t = 5
    s_i = random_scalar()
    shares, commitments = share_secret(s_i, list(range(1, n + 1)), t)
    assert len(shares) == n
    assert len(commitments) == t + 1


def test_share_verification():
    n = 10
    t = 5
    s_i = random_scalar()
    shares, commitments = share_secret(s_i, list(range(1, n + 1)), t)

    for j, s_ij in shares.items():
        assert verify_share(j, s_ij, commitments)


def test_share_verification_invalid_commitments():
    n = 10
    t = 5
    s_i = random_scalar()
    shares, commitments = share_secret(s_i, list(range(1, n + 1)), t)
    commitments[0] = multiply(commitments[0], 2)

    for j, s_ij in shares.items():
        assert not verify_share(j, s_ij, commitments)


def test_recover_secret():
    n = 10
    t = 5
    s_i = random_scalar()
    shares, _ = share_secret(s_i, list(range(1, n + 1)), t)
    shares_for_recovery = dict(random.sample(shares.items(), t + 1))
    assert s_i == recover_secret(shares_for_recovery)


def test_shared_key_derivation():
    sk_i, pk_i = keygen()
    sk_j, pk_j = keygen()
    k_ij = shared_key(sk_i, pk_j)
    k_ji = shared_key(sk_j, pk_i)
    assert normalize(k_ij) == normalize(k_ji)


def test_encryption_of_share():
    sk_i, pk_i = keygen()
    sk_j, pk_j = keygen()
    j = 17
    s_ij = 4711
    k_ij = shared_key(sk_i, pk_j)
    es_ij = encrypt_share(s_ij, k_ij, j)
    k_ij_for_decryption = shared_key(sk_j, pk_i)
    ds_ij = decrypt_share(es_ij, k_ij_for_decryption, j)
    assert s_ij == ds_ij


def test_dleq():
    alpha = 17
    X1 = G1
    X2 = multiply(G1, 4711)
    Y1 = multiply(X1, alpha)
    Y2 = multiply(X2, alpha)

    c, r = dleq(X1, Y1, X2, Y2, alpha)
    assert dleq_verify(X1, Y1, X2, Y2, c, r)
    assert not dleq_verify(multiply(G1, 2), Y1, X2, Y2, c, r)


def test_sum_points():
    assert normalize(sum_points([G1, G1, multiply(G1, 2)])) == normalize(multiply(G1, 4))


def test_full_protocol_all_honest():
    # SETUP
    n = 10
    t = 5
    nodes = list(range(1, n + 1))
    secret_keys, public_keys = {}, {}
    for i in nodes:
        secret_keys[i], public_keys[i] = keygen()

    # SHARE DISTRIBUTION PHASE
    secrets, shares, commitments = {}, {}, {}
    for i in nodes:
        secrets[i] = random_scalar()
        shares[i], commitments[i] = share_secret(secrets[i], list(range(1, n + 1)), t)

    # share encryption (node i encrypts shares for all nodes j != i)
    encrypted_shares = defaultdict(dict)
    for i in nodes:
        for j in nodes:
            if i != j:
                k_ij = shared_key(secret_keys[i], public_keys[j])
                encrypted_shares[i][j] = encrypt_share(shares[i][j], k_ij, j)

    # share decryption (node j decrypts all shares it received)
    decrypted_shares = defaultdict(dict)
    for j in nodes:
        for i in nodes:
            if i != j:
                k_ij = shared_key(secret_keys[i], public_keys[j])
                decrypted_shares[i][j] = decrypt_share(encrypted_shares[i][j], k_ij, j)
                assert decrypted_shares[i][j] == shares[i][j]

    # share verification (node j checks all shares it received)
    for j in nodes:
        for i in nodes:
            if i != j:
                assert verify_share(j, shares[i][j], commitments[i])

    # DISPUTE PHASE
    # NO DISPUTES IN THIS TEST SCENARIO

    # KEY DERIVATION PHASE

    # proving h_values for key derivation
    h_values, h_proofs = {}, {}
    for i in nodes:
        h_values[i] = multiply(H1, secrets[i])
        h_proofs[i] = dleq(H1, h_values[i], G1, commitments[i][0], secrets[i])

    # verification of the h_values (executed by all nodes)
    for i in nodes:
        challenge, response = h_proofs[i]
        assert dleq_verify(H1, h_values[i], G1, commitments[i][0], challenge, response)

    # recover of values not required for this all honest test

    # compute master key
    master_secret_key = sum_scalars(secrets.values())
    master_public_key = sum_points(h_values.values())
    assert normalize(multiply(H1, master_secret_key)) == normalize(master_public_key)

    # compute group keys
    group_secret_keys = {j: sum_scalars(shares[i][j] for i in nodes) for j in nodes}
    group_public_keys = {j: multiply(H1, group_secret_keys[j]) for j in nodes}

    # test recovery of master secret key from t + 1 group secret keys
    group_secret_keys_for_recovery = {j: group_secret_keys[j] for j in random.sample(nodes, t + 1)}
    recovered_master_secret_key = recover_secret(group_secret_keys)
    assert master_secret_key == recovered_master_secret_key


def test_pairing():
    sk = random_scalar()
    pk1 = multiply(G1, sk)
    pk2 = multiply(G2, sk)
    assert pairing(G2, pk1) == pairing(pk2, G1)
    assert pairing(H2, pk1) == pairing(pk2, H1)


def test_evaluate_public_polynomial():
    s = random_scalar()
    shares, commitments = share_secret(s, list(range(1, 11)), 5)
    assert normalize(multiply(G1, shares[3])) == normalize(
        evaluate_public_polynomial(3, commitments)
    )
