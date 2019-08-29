from crypto import *
from crypto import _wrap, _unwrap
from py_ecc import bn128


def test_wrapping():

    assert bn128.G1 == _wrap(G1)
    assert bn128.G2 == _wrap(G2)
    assert _unwrap(bn128.G1) == G1
    assert _unwrap(bn128.G2) == G2


def test_pairing_check_pyecc():
    sk = random_scalar(seed=1)
    pk = bn128.multiply(bn128.G1, sk)
    bls_pk = bn128.multiply(bn128.G2, sk)
    assert bn128.pairing(bn128.G2, pk) == bn128.pairing(bls_pk, bn128.G1)


def test_pairing_check():
    sk = random_scalar(seed=1)
    pk = multiply(G1, sk)
    bls_pk = multiply(neg(G2), sk)
    assert check_pairing(pk, G2, G1, bls_pk)
