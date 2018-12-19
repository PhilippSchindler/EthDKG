from typing import List, Set, Optional, Any

import bls
import vss
import crypto
from crypto import (
    neg,
    multiply,
    G1,
    G2,
    PointG1,
    PointG2,
)


class Node:

    ###########################################################################
    # GENERAL

    n: int   # total number of participants in the protocol, assigned after registration phase
    t: int   # secret sharing threshold, assigned after registration phase, typically t = floor(n / 2) + 1

    id: int  # id the node (from {1, 2, ... n}), assigned after successful registration in the smart contract

    @property
    def idx(self) -> int:
        return self.id - 1

    account: str    # Ethereum account address

    ###########################################################################
    # CRYPTOGRAPHIC KEYS

    sk: int                 # the node's personal secret key
    pk: PointG1             # the node's personal public key (from group G1)
    bls_pk: PointG2         # the node's personal bls public keys (from group G2)

    group_sk: int            # the node's individual aggregated secret key (assigned after DKG completed)
    group_pk: PointG1        # the node's individual aggregated public key (assigned after DKG completed)
    group_bls_pk: PointG2    # the node's individual aggregated bls public key (assigned after DKG completed)

    master_pk: PointG1       # the group's common public key (= master key, assigned after DKG completed)
    master_bls_pk: PointG2   # the group's common bls public key (= master key assigned after DKG completed)

    ###########################################################################
    # COEFFICIENTS

    # list of t-1 coefficients, defining the nodes secret polynom
    # does not include the first coefficient (which is the secret key)
    # _coefficients: List[int]

    # list of t commitments to the coefficients of the secret polynom
    # does not include the first coefficient (which is equal to the public key)
    # public_coefficients: List[PointG1]

    ###########################################################################
    # SHARING

    nodes: List                  # list of all registered nodes, nodes[self.idx] == self, assigned after registration
    group: List                  # list of all nodes with completed the sharing phase successfully

    share: int                   # set by other Node instance, which received this share during the key sharing phase
    shares: List[int]
    encrypted_shares: List[int]  # list of encrypted shares of length n-1

    # list of t - 1 points from the secret sharing polynom, used for share verification
    public_coefficients: List[PointG1]

    # results of verification procedures from load_shares
    share_ok: bool
    coefficients_ok: bool

    def __init__(self,
                 id: Optional[int] = None,
                 sk_seed: Optional[int] = None,
                 pk: Optional[PointG1] = None,
                 bls_pk: Optional[PointG2] = None,
                 account: Optional[str] = None) -> None:

        assert pk is None or (id is not None), 'id is required if public key is given'
        assert (pk is None) == (bls_pk is None), 'either provide both pk and bls_pk or none of the two arguments'
        assert not (sk_seed is not None and pk is not None), 'don not provide both sk_seed and public keys'

        if id is not None:
            self.id = id
        self.pk = pk
        self.bls_pk = bls_pk
        if sk_seed is not None:
            self.keygen(sk_seed)

    def __repr__(self):
        id = '<not assigned>'
        if hasattr(self, 'id'):
            id = self.id
        if not hasattr(self, 'sk') or self.sk is None:
            return f'Node(id={id})'
        sks = f'{self.sk:064x}'
        return f'Node(id={id}, sk=0x{sks[:4]}..{sks[-4:]})'

    def registration_info(self) -> 'Node':
        """ returns a copy of the node's public information as registered
        """
        assert self.id is not None
        assert self.pk is not None
        assert self.bls_pk is not None
        copy = Node()
        copy.id = self.id
        copy.pk = self.pk
        copy.bls_pk = self.bls_pk
        return copy

    def keygen(self, seed=None):
        """ generates a new secret/public key pair for the node
        """
        self.sk, self.bls_pk = bls.keygen(seed)
        self.pk = multiply(G1, self.sk)

    def init_secret_sharing(self, nodes: List['Node'], id: int = None, threshold: int = None):
        """ 1. assign the id obtained from the registration to the node
            2. derive/pick secret coefficients to initialize the node's secret polynomial
            3. compute shares of all nodes
            4. compute public coefficients
            5. store the node's share for itself
            Args:
                id: the id the node got assigned during the registration
                nodes: list of all registered nodes
                threshold: number of collaborating nodes required to recover; set to floor(N/2) + 1 if not provided
        """
        assert self.sk is not None, "call to keygen() is required before starting secret sharing"

        if id is not None:
            self.id = id
        assert self.id is not None, 'assignment of an id is required prior to the key sharing operation'

        self.n = len(nodes)
        self.t = threshold or (self.n // 2 + 1)

        self.nodes = [self if node.idx == self.idx else node for node in nodes]
        assert [node.id for node in nodes] == list(range(1, self.n + 1)), 'use of the ids [1, 2, ..., n] is required'

        shares, public_coefficients = vss.share(self.sk, self.n, self.t)

        self.share = shares[self.idx]
        self.share_ok = True
        self.coefficients_ok = True
        self.shares = shares

        # encrypt all shares for OTHER nodes used individual shared keys
        self.encrypted_shares = []
        for node, share in zip(self.nodes, shares):
            if node != self:
                shared_key = vss.shared_key(self.sk, node.pk)
                encrypted_share = vss.encrypt_share(share, node.id, shared_key)
                self.encrypted_shares.append(encrypted_share)

        # remove C0 to form the list of public_coefficients as commitments to the shares,
        # C0 is already given by the node's public keys
        self.public_coefficients = public_coefficients[1:]

    def load_shares(self, issuer_id: int, encrypted_shares: List[int], public_coefficients: List[PointG1]) -> None:
        """ 1. stores the given information
            2. extracts and decrypts the share for the node itself
            3. verifies this share and raises an ValueError if it is not valid
        """
        assert len(encrypted_shares) == self.n - 1, "invalid number of encrypted shares"
        assert len(public_coefficients) == self.t - 1, "invalid number of public_coefficients"

        issuer = self.nodes[issuer_id - 1]
        issuer.encrypted_shares = encrypted_shares
        issuer.public_coefficients = public_coefficients

        share_idx = self.id - 1 if self.id < issuer_id else self.id - 2
        encrypted_share = encrypted_shares[share_idx]
        issuer.share = vss.decrypt_share(encrypted_share, self.id, vss.shared_key(self.sk, issuer.pk))

        # verify that coefficients are valid points
        issuer.coefficients_ok = all(crypto.is_on_curve(c) for c in issuer.public_coefficients)
        issuer.share_ok = issuer.coefficients_ok and vss.verify(
            self.id, issuer.share, public_coefficients=[issuer.pk] + issuer.public_coefficients)

        if not issuer.share_ok:
            raise ValueError("Share verification failed.")

    def load_dispute_infos(self, disputed_node_ids: Set[int]) -> None:
        """ load the dispute information to identify all nodes which performed the key sharing operation as specified,
            i.e. all nodes which
             a) have provide their shares during the key sharing phase and
             b) no dispute against some of their shares was successful during the dispute phase
        """
        offline_node_ids = [node.id for node in self.nodes if not hasattr(node, 'share')]

        self.group = []  # stores all nodes which successfully completed the key sharing and dispute phase
        for node in self.nodes:
            if (node.id in offline_node_ids) or (node.id in disputed_node_ids):
                continue
            self.group.append(node)

        if len(self.group) < self.t:
            raise RuntimeError('not enough nodes have provided valid shares')

    def derive_group_keys(self) -> None:
        """ computes the group public keys and the personal group key for the node itself
        """
        if not hasattr(self, "group"):
            # load_dispute_infos() was not called yet, we use call nodes which provided shares for our group
            # i.e. use the empty set for loading disputes
            self.load_dispute_infos(set())

        self.group_sk = sum([node.share for node in self.group])         # maybe needs to be product instead
        self.group_pk = multiply(G1, self.group_sk)
        self.group_bls_pk = multiply(neg(G2), self.group_sk)

        self.master_pk = crypto.sum_points([node.pk for node in self.group])
        self.master_bls_pk = crypto.sum_points([node.bls_pk for node in self.group])

    def sign(self, message: Any) -> PointG1:
        return bls.sign(self.group_sk, message)
