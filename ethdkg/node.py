from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict

from . import crypto
from .crypto import G1, H1, G2, H2, add, multiply, pairing, normalize
from .crypto import PointG1, PointG2

INVALID_SHARE = -1


class Node:

    n: int
    t: int
    idx: int  # a one based index, typically assigned by the smart contract

    nodes: List[int]  # 1, 2, ..., n
    other_nodes: List[int]  # 1, 2, ... idx-1, idx+1, ..., n
    disputed_nodes: Set[int]  # set of all nodes which have provably shown malicicous behaviour
    qualified_nodes: List[int]  # list of all nodes which contribute to the master key

    secret: int
    secret_key: int  # the node's personal secret key
    public_key: PointG1  # the node's personal public key (from group G1)
    public_keys: Dict[int, PointG1]  # the public keys for all registered nodes
    shared_keys: Dict[int, PointG1]  # the shared keys between this and all other nodes, used for sym. encryption

    shares: Dict[int, int]  # shares set out by this node
    decrypted_shares: Dict[int, int]  # shares for this node
    encrypted_shares: Dict[int, Dict[int, int]]  # all encrypted shares (for all to all nodes)
    commitments: Dict[int, List[PointG1]]  # the commitments to the coeffcients sent out alongside the encrypted shares

    key_shares: Dict[int, Tuple[PointG1, PointG2]]
    decrypted_shares_for_recovery: Dict[int, Dict[int, int]]  # [idx of recovered node][idx of recovering node]
    recovered_key_share_secrets: Dict[int, int]

    master_public_key: PointG2
    group_secret_key: int
    group_public_key: PointG2
    group_public_key_in_G1: PointG1
    group_public_key_correctness_proof: Tuple[int, int]

    # ONLY EVER ACTIVATE THIS FLAGS DURING EVALUATION, NOT FOR PRODUCTION USE!!!
    _disable_share_verification = False
    _disable_dispute_verification = False
    _disable_key_share_verification = False
    _disable_recovery_share_verification = False

    def __init__(self):
        self.secret = crypto.random_scalar()
        self.secret_key, self.public_key = crypto.keygen()
        self.decrypted_shares_for_recovery = defaultdict(dict)

    def setup(self, n: int, t: int, assigned_idx_for_this_node: int, public_keys: Dict[int, PointG1]):
        """ Initialization step of the DKG protocol.
            Executed after all nodes have registered with their public keys pk1, 
            and the DKG prameter are defined.
        """
        self.n = n
        self.t = t
        self.idx = assigned_idx_for_this_node
        self.nodes = list(public_keys)  # the indices or addresses
        self.other_nodes = [i for i in self.nodes if i != self.idx]
        self.public_keys = public_keys
        self.shared_keys = {j: crypto.shared_key(self.secret_key, public_keys[j]) for j in self.other_nodes}
        self.disputed_nodes = set()
        self.key_shares = {}
        self.recovered_key_share_secrets = {}

    def compute_shares(self) -> Tuple[Dict[int, int], List[PointG1]]:
        """ Performs the share distribution step of the protocol. 
            Returns: 
                - the encrypted shares 
                - the commitments to the coefficients of the underlying secert sharing polynomial
        """
        self.shares, commitments = crypto.share_secret(self.secret, self.nodes, self.t)

        # one share for oneself
        self.decrypted_shares = {self.idx: self.shares[self.idx]}
        self.commitments = {self.idx: commitments}

        # the other shares are encrypted and sent out
        encrypted_shares = {j: crypto.encrypt_share(self.shares[j], self.shared_keys[j], j) for j in self.other_nodes}
        self.encrypted_shares = {self.idx: encrypted_shares}
        return encrypted_shares, commitments

    def load_shares(self, issuer_idx: int, encrypted_shares: Dict[int, int], commitments: List[PointG1]) -> bool:
        """ Stores the given encrypted shares.
            Also decrypt and verfify the share for this node.
            If it is found invalid, this fact is also stored for later dispute.
        """
        assert len(encrypted_shares) == self.n - 1
        assert issuer_idx not in encrypted_shares
        assert all([i in encrypted_shares for i in self.nodes if i != issuer_idx])
        assert issuer_idx != self.idx

        self.encrypted_shares[issuer_idx] = encrypted_shares
        self.commitments[issuer_idx] = commitments

        share = crypto.decrypt_share(encrypted_shares[self.idx], self.shared_keys[issuer_idx], self.idx)
        if self._disable_share_verification or crypto.verify_share(self.idx, share, commitments):
            self.decrypted_shares[issuer_idx] = share
            return True
        else:
            self.decrypted_shares[issuer_idx] = INVALID_SHARE
            return False

    def compute_disputes(self) -> Dict[int, Tuple[PointG1, Tuple[int, int]]]:
        """ Returns proofs of invalidity for all loaded shares which have been found invalid. 
            Returns an empty list of all loaded shares have been found valid.
        """
        self.disputed_nodes = set()
        dispute_proofs = {}
        for issuer_idx, share in self.decrypted_shares.items():
            if share is INVALID_SHARE:
                self.disputed_nodes.add(issuer_idx)
                shared_key = self.shared_keys[issuer_idx]
                shared_key_correctness_proof = crypto.dleq(
                    G1, self.public_key, self.public_keys[issuer_idx], shared_key, self.secret_key
                )
                dispute_proofs[issuer_idx] = shared_key, shared_key_correctness_proof
        return dispute_proofs

    def load_dispute(
        self, issuer_idx: int, disputer_idx: int, shared_key: PointG1, shared_key_correctness_proof: Tuple[int, int]
    ) -> bool:
        """ Verifies the correctness the given dispute. 
            Marks the issuer as adversarial in case the dispute is valid.
        """
        if self._disable_dispute_verification:
            self.disputed_nodes.add(issuer_idx)
            return True

        challenge, response = shared_key_correctness_proof
        if not crypto.dleq_verify(
            G1, self.public_keys[disputer_idx], self.public_keys[issuer_idx], shared_key, challenge, response
        ):
            return False  # dispute is invalid because the proved shared key is not proven correct

        disputed_share = crypto.decrypt_share(self.encrypted_shares[issuer_idx][disputer_idx], shared_key, disputer_idx)

        if crypto.verify_share(disputer_idx, disputed_share, self.commitments[issuer_idx]):
            return False  # dispute is invalid because share is valid

        # dispute sucessfully verified as the shared key is valid while the decrypted share is indeed found invalid
        self.disputed_nodes.add(issuer_idx)
        return True

    def compute_qualified_nodes(self) -> List[int]:
        self.qualified_nodes = [i for i in self.nodes if i in self.encrypted_shares and i not in self.disputed_nodes]
        return self.qualified_nodes

    def compute_key_share(self, recovered_node_idx: Optional[int] = None) -> Tuple[PointG1, Tuple[int, int], PointG2]:
        h1 = multiply(H1, self.secret)
        h1_proof = crypto.dleq(H1, h1, G1, self.commitments[self.idx][0], self.secret)
        h2 = multiply(H2, self.secret)
        self.key_shares = {self.idx: (h1, h2)}
        return h1, h1_proof, h2

    def load_key_share(self, issuer_idx: int, h1: PointG1, h1_proof: Tuple[int, int], h2: PointG2) -> bool:
        if self._disable_key_share_verification:
            self.key_shares[issuer_idx] = h1, h2
            return True

        assert issuer_idx in self.qualified_nodes

        challenge, response = h1_proof
        if not crypto.dleq_verify(H1, h1, G1, self.commitments[issuer_idx][0], challenge, response):
            return False
        if pairing(H2, h1) != pairing(h2, H1):
            return False

        self.key_shares[issuer_idx] = h1, h2
        return True

    def initiate_key_share_recovery(self, node_idx: int):
        """ Returns the shared key (and correctness proof) required to recover the key_shares.
        """
        shared_key = self.shared_keys[node_idx]
        shared_key_correctness_proof = crypto.dleq(
            G1, self.public_key, self.public_keys[node_idx], shared_key, self.secret_key
        )
        return shared_key, shared_key_correctness_proof

    def load_recovered_key_share(
        self, node_idx: int, recoverer_idx: int, shared_key: PointG1, shared_key_correctness_proof: Tuple[int, int]
    ) -> bool:
        challenge, response = shared_key_correctness_proof
        if not crypto.dleq_verify(
            G1, self.public_keys[recoverer_idx], self.public_keys[node_idx], shared_key, challenge, response
        ):
            return False

        decrypted_share = crypto.decrypt_share(
            self.encrypted_shares[node_idx][recoverer_idx], shared_key, recoverer_idx
        )
        if not self._disable_recovery_share_verification:
            if not crypto.verify_share(recoverer_idx, decrypted_share, self.commitments[node_idx]):
                return False

        # only store the share if we do not already have t + 1 valid shares
        if len(self.decrypted_shares_for_recovery[node_idx]) < self.t + 1:
            self.decrypted_shares_for_recovery[node_idx][recoverer_idx] = decrypted_share

        return True

    def recover_key_share(self, node_idx: int) -> bool:
        """ Tries to compute the key_shares from the stored recovered shares. 
            Returns False if the process failed as not enough shares are available.
        """
        if len(self.decrypted_shares_for_recovery[node_idx]) < self.t + 1:
            return False
        if node_idx in self.recovered_key_share_secrets:
            # already recovered previously, no need to compute the secret again
            return True

        recovered_secret = crypto.recover_secret(self.decrypted_shares_for_recovery[node_idx])
        self.recovered_key_share_secrets[node_idx] = recovered_secret
        self.key_shares[node_idx] = multiply(H1, recovered_secret), multiply(H2, recovered_secret)
        return True

    def derive_master_public_key(self):
        self.master_public_key = crypto.sum_points(h2 for _, h2 in self.key_shares.values())
        return self.master_public_key

    def derive_group_keys(self):
        self.group_secret_key = crypto.sum_scalars(self.decrypted_shares[i] for i in self.qualified_nodes)
        self.group_public_key = multiply(H2, self.group_secret_key)
        self.group_public_key_in_G1 = multiply(H1, self.group_secret_key)
        self.group_public_key_correctness_proof = crypto.dleq(
            G1, multiply(G1, self.group_secret_key), H1, self.group_public_key_in_G1, self.group_secret_key
        )

    def verify_group_public_key(self, node_idx: int, group_public_key: PointG2, gpk_h: PointG1, proof: Tuple[int, int]):
        """ Verify the given group public key for node j.
            1. compute g1 ^ sum(s_i->j)  for i in Q (via evaluation of the public polynomial defined by the commitments)
            2. verify DLEQ proof for base change from g to h
            3. use pairing to check the move from group 1 to group 2
        """
        vg = crypto.sum_points(
            crypto.evaluate_public_polynomial(node_idx, self.commitments[qualified_node_idx])
            for qualified_node_idx in self.qualified_nodes
        )
        # vg = crypto.evaluate_public_polynomial(node_idx, self.commitments[node_idx])
        challenge, response = proof
        if not crypto.dleq_verify(G1, vg, H1, gpk_h, challenge, response):
            return False
        return pairing(H2, gpk_h) == pairing(group_public_key, H1)

