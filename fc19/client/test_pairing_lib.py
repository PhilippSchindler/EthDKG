from py_ecc.bn128 import G1, G2, neg, multiply, pairing


def test_pairing_python():
    assert pairing(G2, multiply(G1, 5)) == pairing(multiply(G2, 5), G1)


def test_pairing_python_neg():
    assert pairing(G2, multiply(G1, 5)) != pairing(multiply(G2, 5), neg(G1))
