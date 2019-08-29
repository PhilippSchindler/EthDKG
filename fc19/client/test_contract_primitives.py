import utils
import vss
from crypto import G1, G2, add, neg, multiply, random_scalar, check_pairing


w3 = utils.connect()
contract = utils.deploy_contract('DKG')


def test_add():
    a = multiply(G1, 5)
    b = multiply(G1, 10)
    s = add(a, b)
    assert contract.bn128_add([a[0], a[1], b[0], b[1]]) == list(s)


def test_multiply():
    assert G1 == (1, 2)
    assert contract.bn128_multiply([1, 2, 5]) == list(multiply(G1, 5))


def test_check_pairing():
    P1 = multiply(G1, 5)
    Q1 = G2
    Q2 = multiply(neg(G2), 5)
    P2 = G1
    assert check_pairing(P1, Q1, P2, Q2)


def test_verify_decryption_key():
    sk1, sk2 = random_scalar(), random_scalar()
    pk1, pk2 = multiply(G1, sk1), multiply(G1, sk2)

    shared_key = vss.shared_key(sk1, pk2)
    chal, resp = vss.shared_key_proof(sk1, pk2)

    assert vss.dleq_verify(G1, pk1, pk2, shared_key, chal, resp)
    assert contract.verify_decryption_key(
        shared_key,
        [chal, resp],
        pk1,
        pk2
    )


def test_verify_sk_knowledge():
    sk = random_scalar()
    pk = multiply(G1, sk)
    addr = w3.eth.accounts[0]

    proof = vss.prove_sk_knowledge(sk, pk, addr)
    assert vss.verify_sk_knowledge(pk, proof[0], proof[1], addr)

    print("sk", sk)
    print("pk", pk)
    print("account", addr)
    print("proof", proof)

    assert contract.verify_sk_knowledge(pk, proof)
