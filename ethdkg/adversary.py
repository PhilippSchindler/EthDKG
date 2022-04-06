from . import logging
from .ethnode import EthNode, point_to_eth


class Adversary_SendInvalidShares(EthNode):
    def __init__(self, address, contract, logger=logging.NullLogger, targets=None):
        super().__init__(address, contract, logger)
        self.targets = targets or []

    def distribute_shares(self, sync=False):
        encrypted_shares, commitments = super().compute_shares()

        if self.targets:
            self.logger.newline()
        else:
            self.logger.warning("No attack targets specified!")

        for t in self.targets:
            # contains either the node's 0-based number (in order of registrion) or address
            target = t

            if isinstance(target, int):
                target = self.nodes[target]
            else:
                target = int(target, 16)

            if target in encrypted_shares:
                self.logger.info(f"MANIPULATING SHARE FOR NODE {self.addresses[target]}")
                encrypted_shares[target] += 1
            else:
                self.logger.error(f"attack target {t} not found / invalid, continuing without this target")

        if self.targets:
            self.logger.newline()

        return super().distribute_shares(encrypted_shares, commitments, sync=sync)


class Adversary_AbortOnKeyShareSubmission(EthNode):
    def submit_key_share(self, recovered_node_idx=None, sync=False):
        self.logger.newline()
        self.logger.critical("not submitting key share")
        self.logger.critical("aborting protocol")
        exit(0)


class Adversary_AbortAfterRegistration(EthNode):
    def setup(self):
        self.logger.newline()
        self.logger.critical("aborting protocol")
        exit(0)
