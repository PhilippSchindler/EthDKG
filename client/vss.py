from typing import List, Tuple
import sympy

from crypto import (
    CURVE_ORDER,
    G1,
    add,
    multiply,
    hash_to_scalar,
    random_scalar,
    PointG1,
    keccak_256,
    soliditySha3,
)


def share(secret: int, n: int, t: int) -> Tuple[List[int], List[PointG1]]:
    """ computes n shares of a given secret such that at least t shares are required for recovery of the secret
        additionally returns the public_coefficients used to verify the validity of the shares
    """
    coefficients = [secret] + [hash_to_scalar(f"vss:coefficient:{secret}:{j}") for j in range(1, t)]

    def f(x):
        """ secret polynomial
        """
        return sum(coef * pow(x, j, CURVE_ORDER) for j, coef in enumerate(coefficients)) % CURVE_ORDER

    shares = [f(id) for id in range(1, n + 1)]
    public_coefficients = [multiply(G1, coef) for coef in coefficients]

    return shares, public_coefficients


def verify(share_id: int, share: int, public_coefficients: List[PointG1]) -> bool:
    """ check share validity and return True if the share is valid, False otherwise
    """
    def F(x):
        """ public polynomial
        """
        result = public_coefficients[0]
        for j, coef in enumerate(public_coefficients[1:]):
            result = add(result, multiply(coef, pow(x, j + 1, CURVE_ORDER)))
        return result

    return F(share_id) == multiply(G1, share)


def recover(id_and_share_list: List[Tuple[int, int]]) -> int:
    indices = [j for j, _ in id_and_share_list]
    return sum(share * lagrange_coefficient(i, indices) for i, share in id_and_share_list) % CURVE_ORDER


def recover_point(id_and_point_list: List[Tuple[int, PointG1]]) -> PointG1:
    ids = [j for j, _ in id_and_point_list]
    i, sig = id_and_point_list[0]
    result = multiply(sig, lagrange_coefficient(i, ids))
    for i, sig in id_and_point_list[1:]:
        t = multiply(sig, lagrange_coefficient(i, ids))
        result = add(result, t)
    return result


def lagrange_coefficient(i: int, ids: List[int]) -> int:
    result = 1
    for j in ids:
        if i != j:
            result *= j * sympy.mod_inverse((j - i) % CURVE_ORDER, CURVE_ORDER)
            result %= CURVE_ORDER
    return result


def encrypt_share(share: int, receiver_id: int, shared_key: PointG1) -> int:
    """ encrypts a share given the provided shared key
        receiver_id added as argument to the hash function to ensure that shares from A->B and B->A
        are encrypted using a different key
    """
    sx = shared_key[0]
    hx = keccak_256(sx.to_bytes(32, "big") + receiver_id.to_bytes(32, "big")).digest()
    return share ^ int.from_bytes(hx, "big")


decrypt_share = encrypt_share


def shared_key(sk, other_pk: PointG1) -> PointG1:
    """ Computes a shared key between given a node's secret key and and some other node public key.
        Used for individual encryption/decryption of the shares.
    """
    return multiply(other_pk, sk)


def shared_key_proof(sk, other_pk: PointG1) -> Tuple[int, int]:
    """ non-iteractive zero-knowledge proof showing that
        shared_key(sk, other_pk) is indeed the correct encryption/decryption key
    """
    pk = multiply(G1, sk)
    shared_key = multiply(other_pk, sk)
    return dleq(G1, pk, other_pk, shared_key, alpha=sk)


def prove_sk_knowledge(sk: int, pk: PointG1, account: str = None) -> Tuple[int, int]:
    """ proofs that the caller knows the discreate logarithm of pk to the generator g1
        (and that links the proof to an Ethereum account if provided)
    """
    w = random_scalar()
    t = multiply(G1, w)

    types = ["uint256"] * 6
    values = list(G1 + pk + t)
    if account is not None:
        types.append("address")
        values.append(account)

    c = soliditySha3(abi_types=types, values=values)
    c = int.from_bytes(c, "big")

    r = (w - sk * c) % CURVE_ORDER
    return c, r


def verify_sk_knowledge(pk: PointG1, challenge: int, response: int, account: str = None) -> bool:

    t = add(multiply(G1, response), multiply(pk, challenge))

    types = ["uint256"] * 6
    values = list(G1 + pk + t)
    if account is not None:
        types.append("address")
        values.append(account)

    c = soliditySha3(abi_types=types, values=values)
    c = int.from_bytes(c, "big")

    print("values", values)

    print("t", t)
    print("c", c)

    return c == challenge


def dleq(g1: PointG1, h1: PointG1, g2: PointG1, h2: PointG1, alpha: int) -> Tuple[int, int]:
    """ dleq... discrete logarithm equality
        proofs that the caller knows alpha such that h1 = g1**alpha  and  h2 = g2**alpha
        without revealing alpha
    """
    w = random_scalar()
    a1 = multiply(g1, w)
    a2 = multiply(g2, w)
    c = soliditySha3(  # pylint: disable=E1120
        abi_types=["uint256"] * 12,  # 12,
        values=[
            a1[0],
            a1[1],
            a2[0],
            a2[1],
            g1[0],
            g1[1],
            h1[0],
            h1[1],
            g2[0],
            g2[1],
            h2[0],
            h2[1],
        ],
    )
    c = int.from_bytes(c, "big")
    r = (w - alpha * c) % CURVE_ORDER
    return c, r


def dleq_verify(g1: PointG1, h1: PointG1, g2: PointG1, h2: PointG1, challenge: int, response: int):
    a1 = add(multiply(g1, response), multiply(h1, challenge))
    a2 = add(multiply(g2, response), multiply(h2, challenge))
    c = soliditySha3(  # pylint: disable=E1120
        abi_types=["uint256"] * 12,  # 12,
        values=[
            a1[0],
            a1[1],
            a2[0],
            a2[1],
            g1[0],
            g1[1],
            h1[0],
            h1[1],
            g2[0],
            g2[1],
            h2[0],
            h2[1],
        ],
    )
    c = int.from_bytes(c, "big")
    return c == challenge
