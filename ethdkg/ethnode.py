import math
import time
from typing import List, Tuple


from .node import Node
from .crypto import PointG1, PointG2, FQ, FQ2, G1, H1, normalize
from . import utils
from . import crypto
from . import logging
from .state_updates import StateUpdate


def point_to_eth(p: PointG1) -> Tuple[int, int]:
    pn = normalize(p)
    return int(pn[0]), int(pn[1])


def point_from_eth(p) -> PointG1:
    x, y = p
    return (FQ(x), FQ(y), FQ(1))


def point_G2_to_eth(p: PointG2) -> Tuple[int, int, int, int]:
    x, y = normalize(p)
    a, ai = x.coeffs[0], x.coeffs[1]  # ordering: real, imag
    b, bi = y.coeffs[0], y.coeffs[1]  # ordering: real, imag
    return ai, a, bi, b  # ordering flipped for representation in contract!


def point_G2_from_eth(p) -> PointG2:
    ai, a, bi, b = p
    return (FQ2([a, ai]), FQ2([b, bi]), FQ2((1, 0)))


class EthNode(Node):
    def __init__(self, address, contract, logger=logging.NullLogger):
        super().__init__()
        self.address = address
        self.contract = contract
        self.DELTA_CONFIRM = contract.caller.DELTA_CONFIRM()
        self.DELTA_INCLUDE = contract.caller.DELTA_INCLUDE()
        self.T_REGISTRATION_END = contract.caller.T_REGISTRATION_END()
        self.T_SHARE_DISTRIBUTION_END = contract.caller.T_SHARE_DISTRIBUTION_END()
        self.T_DISPUTE_END = contract.caller.T_DISPUTE_END()
        self.T_KEY_SHARE_SUBMISSION_END = self.T_DISPUTE_END + self.DELTA_CONFIRM + self.DELTA_INCLUDE
        self.logger = logger

    @property
    def tx_registration_receipt(self):
        if self._tx_registration_receipt:
            return self._tx_registration_receipt
        return utils.wait_for_tx_receipt(self.tx_registration_hash)

    def register(self, sync=False):
        public_key = point_to_eth(self.public_key)
        return self.contract.register(public_key).call(self.address, sync)

    def setup(self):
        # wait until the registration phase ended and all registration are confirmed for sure
        utils.wait_for_block(self.T_REGISTRATION_END + self.DELTA_CONFIRM)

        self.n = self.contract.caller.num_nodes()
        self.t = math.ceil(self.n / 2) - 1

        addresses = [self.contract.caller.addresses(i) for i in range(self.n)]
        public_keys = {
            int(addr, 16): point_from_eth(
                (self.contract.caller.public_keys(addr, 0), self.contract.caller.public_keys(addr, 1))
            )
            for addr in addresses
        }

        self.addresses = {int(addr, 16): addr for addr in addresses}

        idx = int(self.address, 16)
        super().setup(self.n, self.t, idx, public_keys)

    def distribute_shares(self, encrypted_shares=None, commitments=None, sync=False):
        if encrypted_shares is None:
            encrypted_shares, commitments = super().compute_shares()

        encrypted_shares = list(encrypted_shares.values())
        self.logger.info(f"encrypted shares: {encrypted_shares}")
        self.logger.info(f"commitments:      {commitments}")
        commitments = [point_to_eth(c) for c in commitments]
        return self.contract.distribute_shares(encrypted_shares, commitments).call(self.address, sync)

    def load_shares(self):
        utils.wait_for_block(self.T_SHARE_DISTRIBUTION_END + self.DELTA_CONFIRM)
        events = self.contract.events.ShareDistribution.createFilter(fromBlock=0).get_all_entries()
        # TODO: limit lookup to time of contract creation (or beginning of share distribution phase)
        #       to the end of the share distribution phase.
        for e in events:
            issuer = int(e.args.issuer, 16)
            if issuer == self.idx:
                continue
            receivers = (node for node in self.nodes if node != issuer)
            encrypted_shares = dict(zip(receivers, e.args.encrypted_shares))
            commitments = [point_from_eth(p) for p in e.args.commitments]
            super().load_shares(issuer, encrypted_shares, commitments)

    def submit_disputes(self, disputes=None, sync=False):
        if disputes is None:
            disputes = super().compute_disputes()
        txs = {}
        for issuer, dispute in disputes.items():
            shared_key = point_to_eth(dispute[0])
            shared_key_correctness_proof = dispute[1]
            receivers = (node for node in self.nodes if node != issuer)
            encrypted_shares = [self.encrypted_shares[issuer][r] for r in receivers]
            commitments = [point_to_eth(p) for p in self.commitments[issuer]]

            self.logger.newline()
            self.logger.info(f"dispute against node {self.addresses[issuer]}")
            self.logger.info(f"    encrypted shares:  {encrypted_shares}")
            self.logger.info(f"    commitments:       {commitments}")
            self.logger.info(f"    shared key:        {shared_key}")
            self.logger.info(f"    correctness proof: {shared_key_correctness_proof}")

            txs[issuer] = self.contract.submit_dispute(
                self.addresses[issuer],
                list(self.addresses.keys()).index(issuer),
                list(self.addresses.keys()).index(self.idx),
                encrypted_shares,
                commitments,
                shared_key,
                shared_key_correctness_proof,
            ).call(self.address, sync)
        return txs

    def load_disputes(self):
        utils.wait_for_block(self.T_DISPUTE_END + self.DELTA_CONFIRM)
        # TODO: limit lookup to time of contract creation (or beginning of share distribution phase)
        #       to the end of the share distribution phase.
        events = self.contract.events.Dispute.createFilter(fromBlock=0).get_all_entries()

        if events:
            self.logger.error(f"{len(events)} dispute events detected")
            self.logger.newline()
        else:
            self.logger.info(f"no dispute events detected")

        for e in events:
            issuer_idx = int(e.args.issuer, 16)
            disputer_idx = int(e.args.disputer, 16)
            shared_key = point_from_eth(e.args.shared_key)
            shared_key_correctness_proof = e.args.shared_key_correctness_proof
            if super().load_dispute(issuer_idx, disputer_idx, shared_key, shared_key_correctness_proof):
                self.logger.info(
                    f"dispute against {e.args.issuer} successfully verified; submitted by {e.args.disputer}"
                )
            else:
                self.logger.critical(
                    f"failed to verify dispute, python and smart contract implementation are inconsistent; dispute against {e.args.issuer}, submitted by {e.args.disputer}"
                )
                exit(1)

    def submit_key_share(self, recovered_node_idx=None, sync=False):
        """ Sends the key share h^(s_i) with the corresponding proof to the smart contracts.
            If a recovered_node_idx is given, instead the recovered values for this node are 
            uploaded.
        """
        if recovered_node_idx is None:
            issuer = self.address
            key_share_G1, key_share_G1_correctness_proof, key_share_G2 = super().compute_key_share()
        else:
            issuer = self.addresses[recovered_node_idx]
            key_share_G1, key_share_G2 = self.key_shares[recovered_node_idx]
            key_share_G1_correctness_proof = crypto.dleq(
                H1,
                key_share_G1,
                G1,
                self.commitments[recovered_node_idx][0],
                self.recovered_key_share_secrets[recovered_node_idx],
            )

        key_share_G1 = point_to_eth(key_share_G1)
        key_share_G2 = point_G2_to_eth(key_share_G2)

        self.logger.info(f"    keyshare (G1):    {key_share_G1}")
        self.logger.info(f"    keyshare (G2):    {key_share_G2}")
        self.logger.info(f"    correctess proof: {key_share_G1_correctness_proof}")

        return self.contract.submit_key_share(issuer, key_share_G1, key_share_G1_correctness_proof, key_share_G2).call(
            self.address, sync
        )

    def load_key_shares(self):
        utils.wait_for_block(self.T_KEY_SHARE_SUBMISSION_END + self.DELTA_CONFIRM)
        # TODO: limit lookup to time of contract creation (or beginning of share distribution phase)
        events = self.contract.events.KeyShareSubmission.createFilter(fromBlock=0).get_all_entries()

        if len(events) > self.t:
            logfunc = self.logger.info if len(events) == len(self.qualified_nodes) else self.logger.warning
            logfunc(
                f"{len(events)} key share submission events detected; " f"{len(self.qualified_nodes)} events expected"
            )
            self.logger.newline()
        else:
            self.logger.critical(f"only {len(events)} event(s) received; at least t + 1 ({self.t + 1}) events required")
            exit(1)

        for e in events:
            self.logger.info(f"key share from node {e.args.issuer}")
            self.logger.info(f"    keyshare (G1):    {e.args.key_share_G1}")
            self.logger.info(f"    keyshare (G2):    {e.args.key_share_G2}")
            self.logger.info(f"    correctess proof: {e.args.key_share_G1_correctness_proof}")
            self.logger.newline()
            if not super().load_key_share(
                int(e.args.issuer, 16),
                point_from_eth(e.args.key_share_G1),
                e.args.key_share_G1_correctness_proof,
                point_G2_from_eth(e.args.key_share_G2),
            ):
                self.logger.critical(
                    "failed to load key share, " "python and smart contract implementation are inconsistent"
                )
                exit(1)

    def recover_key_shares(self, sync=False):
        recovered_nodes = []
        shared_keys = []
        shared_key_correctness_proofs = []
        for node in self.qualified_nodes:
            if node not in self.key_shares:
                self.logger.info(f"node {self.addresses[node]}")
                key, proof = super().initiate_key_share_recovery(node)
                key = point_to_eth(key)
                self.logger.info(f"    shared key: {key}")
                self.logger.info(f"    correctness proof: {proof}")
                self.logger.newline()
                recovered_nodes.append(self.addresses[node])
                shared_keys.append(key)
                shared_key_correctness_proofs.append(proof)

        if recovered_nodes:
            return self.contract.recover_key_shares(recovered_nodes, shared_keys, shared_key_correctness_proofs).call(
                self.address, sync
            )

    def load_recovered_key_shares(self, poll_timeout=1.0):
        eventFilter = None
        # will terminate as soon as key_shares for
        while len(self.key_shares) < len(self.qualified_nodes):
            if eventFilter is None:
                eventFilter = self.contract.events.KeyShareRecovery.createFilter(fromBlock=0)
                events = eventFilter.get_all_entries()
            else:
                time.sleep(poll_timeout)
                events = eventFilter.get_new_entries()

            for e in events:
                recoverer_idx = int(e.args.recoverer, 16)
                recovered_nodes = [int(node, 16) for node in e.args.recovered_nodes]
                shared_keys = [point_from_eth(p) for p in e.args.shared_keys]
                shared_key_correctness_proofs = e.args.shared_key_correctness_proofs

                self.logger.info(f"recovery event received from node {self.addresses[recoverer_idx]}")
                self.logger.info(f"    recovered nodes:    {e.args.recovered_nodes}")
                self.logger.info(f"    shared keys:        {e.args.shared_keys}")
                self.logger.info(f"    correctness proofs: {e.args.shared_key_correctness_proofs}")
                self.logger.newline()

                for recovered_node, shared_key, shared_key_correctness_proofs in zip(
                    recovered_nodes, shared_keys, shared_key_correctness_proofs
                ):
                    if recovered_node in self.key_shares:
                        continue

                    success = super().load_recovered_key_share(
                        recovered_node, recoverer_idx, shared_key, shared_key_correctness_proofs
                    )
                    if success:
                        self.logger.info(
                            f"share for recovery of node {self.addresses[recovered_node]}" " successfully verified"
                        )
                        if recovered_node in self.key_shares:
                            self.logger.info("node already recovered")
                        else:
                            if super().recover_key_share(recovered_node):
                                self.logger.info(f"key share recovered: {self.key_shares[recovered_node]}")
                            else:
                                x = len(self.decrypted_shares_for_recovery[recovered_node])
                                self.logger.info(
                                    f"recovery not yet possible; " f"{self.t + 1 - x} additional shares required"
                                )
                    else:
                        self.logger.error(
                            "invalid share for recovery of node " f"{self.addresses[recovered_node]} received"
                        )
                    self.logger.newline()
        self.logger.info("all key shares recovered successfully")
        StateUpdate.KEY_SHARE_RECOVERIES_LOADED()
        self.logger.newline()

    def submit_recovered_key_shares(self, sync=False):
        # TODO: One could implement randomized timings for the submission of the recovered key
        # shares to save gas costs, as each key share only has to be provided by one party.
        return {
            recovered_node_idx: self.submit_key_share(recovered_node_idx, sync)
            for recovered_node_idx in self.recovered_key_share_secrets
        }

    def submit_master_public_key(self, sync=False):
        # TODO: as in submit_recovered_key_shares, randomized timings for submission of the master
        # public key are possible.
        pk_G2 = super().derive_master_public_key()
        pk_G2 = point_G2_to_eth(pk_G2)

        StateUpdate.MASTER_KEY_DERIVED()

        self.logger.info(f"master public key: {pk_G2}")
        self.logger.newline()

        self.logger.info("submitting master public key")
        return self.contract.submit_master_public_key(pk_G2).call(self.address, sync)

