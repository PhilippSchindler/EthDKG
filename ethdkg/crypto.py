import secrets
import sympy  # consider removing this dependency, only needed for mod_inverse
import web3

from typing import Tuple, Dict, List, Iterable, Union
from py_ecc.optimized_bn128 import G1, G2
from py_ecc.optimized_bn128 import add, multiply, neg, normalize, pairing, is_on_curve
from py_ecc.optimized_bn128 import curve_order as CURVE_ORDER
from py_ecc.optimized_bn128 import field_modulus as FIELD_MODULUS

# from py_ecc.typing import Optimized_Point3D, Optimized_FQ, Optimized_FQ2
from py_ecc.typing import Optimized_Point3D
from py_ecc.fields import optimized_bn128_FQ, optimized_bn128_FQ2

# PointG1 = Tuple[FQ, FQ, FQ]
# PointG2 = Tuple[FQ2, FQ2, FQ2]
# FQ = Optimized_FQ
# FQ2 = Optimized_FQ2
# PointG1 = Optimized_Point3D[FQ]
# PointG2 = Optimized_Point3D[FQ2]

PointG1 = Optimized_Point3D[optimized_bn128_FQ]
PointG2 = Optimized_Point3D[optimized_bn128_FQ2]

FQ = optimized_bn128_FQ
FQ2 = optimized_bn128_FQ2

keccak_256 = web3.Web3.solidityKeccak

# fmt: off
# additional generators for BN128
H1 = (
    FQ(9727523064272218541460723335320998459488975639302513747055235660443850046724),
    FQ(5031696974169251245229961296941447383441169981934237515842977230762345915487),
    FQ(1),
)
H2 = (
    FQ2((9110522554455888802745409460679507850660709404525090688071718755658817738702, 14120302265976430476300156362541817133873389322564306174224598966336605751189)),
    FQ2((8015061597608194114184122605728732604411275728909990814600934336120589400179, 21550838471174089343030649382112381550278244756451022825185015902639198926789)),
    FQ2((1, 0))
)
# fmt: on


def random_scalar() -> int:
    """ Returns a random exponent for the BN128 curve, i.e. a random element from Zq.
    """
    return secrets.randbelow(CURVE_ORDER)


def keygen() -> Tuple[int, PointG1]:
    """ Generates a random keypair on the BN128 curve.
        The public key is an element of the group G1.
        This key is used for deriving the encryption keys used to secure the shares.
        This is NOT a BLS key pair used for signing messages.
    """
    sk = random_scalar()
    pk = multiply(G1, sk)
    return sk, pk


def share_secret(
    secret: int, indices: List[int], threshold: int
) -> Tuple[Dict[int, int], List[PointG1]]:
    """ Computes shares of a given secret such that at least threshold + 1 shares are required to 
        recover the secret. Additionally returns the commitents to the coefficient of the polynom
        used to verify the validity of the shares.
    """
    coefficients = [secret] + [random_scalar() for j in range(threshold)]

    def f(x: int) -> int:
        """ evaluation function for secret polynomial
        """
        return (
            sum(coef * pow(x, j, CURVE_ORDER) for j, coef in enumerate(coefficients)) % CURVE_ORDER
        )

    shares = {x: f(x) for x in indices}
    commitments = [multiply(G1, coef) for coef in coefficients]
    return shares, commitments


def _share_secret_int_indices(s_i: int, n: int, t: int) -> Tuple[Dict[int, int], List[PointG1]]:
    """ Computes n shares of a given secret such that at least t + 1 shares are required for recovery 
        of the secret. Additionally returns the commitents to the coefficient of the polynom
        used to verify the validity of the shares.

        Assumes nodes use the indices [1, 2, ..., n].
        See share_secret function of a generalized variant with arbitary indices.
    """
    coefficients = [s_i] + [
        random_scalar() for j in range(t)
    ]  # coefficients c_i0, c_i1, ..., c_it

    def f(x: int) -> int:
        """ evaluation function for secret polynomial
        """
        return (
            sum(coef * pow(x, j, CURVE_ORDER) for j, coef in enumerate(coefficients)) % CURVE_ORDER
        )

    shares = {x: f(x) for x in range(1, n + 1)}
    commitments = [multiply(G1, coef) for coef in coefficients]
    return shares, commitments


def evaluate_public_polynomial(x: int, commitments: List[PointG1]):
    result = commitments[0]
    for k in range(1, len(commitments)):
        result = add(result, multiply(commitments[k], pow(x, k, CURVE_ORDER)))
    return result


def verify_share(j: int, s_ij: int, Cik: List[PointG1]) -> bool:
    """ check share validity and return True if the share is valid, False otherwise
    """
    r = Cik[0]
    for k, c in enumerate(Cik[1:]):
        r = add(r, multiply(c, pow(j, k + 1, CURVE_ORDER)))
    return normalize(multiply(G1, s_ij)) == normalize(r)


def recover_secret(shares: Dict[int, int]) -> int:
    """ Recovers a shared secret from t VALID shares.
    """

    def lagrange_coefficient(i: int) -> int:
        result = 1
        for j in shares:
            if i != j:
                result *= j * sympy.mod_inverse((j - i) % CURVE_ORDER, CURVE_ORDER)
                result %= CURVE_ORDER
        return result

    return sum(share * lagrange_coefficient(i) for i, share in shares.items()) % CURVE_ORDER


def shared_key(sk_i: int, pk_j: PointG1) -> PointG1:
    k_ij = multiply(pk_j, sk_i)
    return k_ij


def encrypt_share(s_ij: int, k_ij: PointG1, j: int) -> int:
    """ Encrypt the given share s_ij using the shared key k_ij.
        As no symmetric key encryption algorithm is natively support in the EVM, 
        the encryption is implemented by and xor-operation and a hash function.
        The parameter j is added to ensure that s_ij and s_ji are xored with different values.
    """
    x = normalize(k_ij)[0].n
    h = keccak_256(abi_types=["uint256", "uint256"], values=[x, j])
    return s_ij ^ int.from_bytes(h, "big")


decrypt_share = encrypt_share


def dleq(x1: PointG1, y1: PointG1, x2: PointG1, y2: PointG1, alpha: int) -> Tuple[int, int]:
    """ DLEQ... discrete logarithm equality
        Proofs that the caller knows alpha such that y1 = x1**alpha and y2 = x2**alpha
        without revealing alpha.
    """
    w = random_scalar()
    a1 = multiply(x1, w)
    a2 = multiply(x2, w)
    c = keccak_256(
        abi_types=["uint256"] * 12,
        values=[
            int(v)
            for v in normalize(a1)
            + normalize(a2)
            + normalize(x1)
            + normalize(y1)
            + normalize(x2)
            + normalize(y2)
        ],
    )
    c = int.from_bytes(c, "big")
    r = (w - alpha * c) % CURVE_ORDER
    return c, r


def dleq_verify(
    x1: PointG1, y1: PointG1, x2: PointG1, y2: PointG1, challenge: int, response: int
) -> bool:
    a1 = add(multiply(x1, response), multiply(y1, challenge))
    a2 = add(multiply(x2, response), multiply(y2, challenge))
    c = keccak_256(  # pylint: disable=E1120
        abi_types=["uint256"] * 12,  # 12,
        values=[
            int(v)
            for v in normalize(a1)
            + normalize(a2)
            + normalize(x1)
            + normalize(y1)
            + normalize(x2)
            + normalize(y2)
        ],
    )
    c = int.from_bytes(c, "big")
    return c == challenge


def sum_scalars(scalars: Iterable[int]):
    return sum(scalars) % CURVE_ORDER


def sum_points(points: Union[Iterable[PointG1], Iterable[PointG2]]):
    result = None
    for p in points:
        if result is None:
            result = p
        else:
            result = add(result, p)
    return result
