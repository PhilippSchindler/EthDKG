import utils
import crypto
from constants import EVENT_REGISTRATION, EVENT_KEY_SHARING, EVENT_DISPUTE_SUCCESSFUL
from node import Node

import vss


class EthNode(Node):

    account: str

    def __init__(self, account: str, *args, **kwargs) -> None:
        self.account = account
        super().__init__(*args, **kwargs)

    def connect(self, contract):
        self.contract = contract

    def register(self, check_contract_phase=True):
        if check_contract_phase:
            assert self.contract.in_registration_phase()

        sk_knowledge_proof = vss.prove_sk_knowledge(self.sk, self.pk, self.account)
        return self.contract.register(
            self.pk, self.bls_pk, sk_knowledge_proof, transact={'from': self.account}
        )

    def init_secret_sharing(self, check_contract_phase=False):
        """ Called after waiting until the registration phase has ended and
            has sufficiently been confirmed in the blockchain.
            Query all registration events from the contract instance to get
               a) the local node id
               b) the number of participanting nodes
               c) the public keys of all participating nodes
        """
        if check_contract_phase:
            assert self.contract.registrations_confirmed()

        id = None
        nodes = []
        events = utils.get_events(self.contract, EVENT_REGISTRATION)
        for e in events:
            args = e['args']
            node = EthNode(
                account=args['node_adr'],
                id=args['id'],
                pk=args['pk'],
                bls_pk=args['bls_pk'],
            )
            if node.account == self.account:
                id = node.id
            nodes.append(node)

        assert id is not None
        super().init_secret_sharing(nodes, id)

    def share_key(self, check_contract_phase=True):
        """ Encrypt and upload the shares, and coefficients for verification.
        """
        if check_contract_phase:
            assert self.contract.registrations_confirmed()

        return self.contract.share_key(
            self.encrypted_shares,
            utils.flatten(self.public_coefficients),
            transact={'from': self.account},
        )

    def load_shares(self, check_contract_phase=True):
        """ Called after waiting until the sharing phase has ended and all submitted shares have
            sufficiently been confirmed in the blockchain.
            All events are proceed, an the shares for the node itself are decrypted, verified and stored.
        """
        if check_contract_phase:
            assert self.contract.sharing_confirmed()

        events = utils.get_events(self.contract, EVENT_KEY_SHARING)
        error = False
        for e in events:
            args = e['args']

            issuer_id = args['issuer']
            if self.id == issuer_id:
                continue

            # load and convert public coefficients to points from group G1
            C = args['public_coefficients']
            C = [(C[i], C[i + 1]) for i in range(0, len(C), 2)]
            try:
                super().load_shares(
                    issuer_id, args['encrypted_shares'], public_coefficients=C
                )
            except ValueError:
                error = True
                pass
        if error:
            raise ValueError('loading of shares triggered verification errors')

    def dispute(self, issuer_id, check_contract_phase=True):
        """ submits a dispute for the given (malicious) share issuer to the smart contract
        """
        if check_contract_phase:
            assert self.contract.sharing_confirmed()

        issuer = self.nodes[issuer_id - 1]

        # distingush between two cases
        # a) the computed public key or (at least one) public coefficient is not a valid elliptic curve point
        for i, c in enumerate(issuer.public_coefficients):
            if not crypto.is_on_curve(c):
                self.contract.dispute_public_coefficient(
                    issuer.account,
                    issuer.encrypted_shares,
                    utils.flatten(issuer.public_coefficients),
                    i,
                    transact={'from': self.account},
                )
                return

        # b) the (encrypted) share is invalid
        return self.contract.dispute_share(
            issuer.account,
            issuer.encrypted_shares,
            utils.flatten(issuer.public_coefficients),
            vss.shared_key(self.sk, issuer.pk),
            vss.shared_key_proof(self.sk, issuer.pk),
            transact={'from': self.account},
        )

    def verify_nodes(self, check_contract_phase=True):
        """ gets all dispute events, and uses this information to derive which nodes should contribute to the group key
        """
        if check_contract_phase:
            assert self.contract.dispute_confirmed()

        dispute_events = utils.get_events(self.contract, EVENT_DISPUTE_SUCCESSFUL)
        dispute_addrs = set(e['args']['bad_issuer_addr'] for e in dispute_events)

        dispute_ids = set()
        for addr in dispute_addrs:
            t = [node for node in self.nodes if node.account == addr]
            assert len(t) == 1, 'above query should always return exactly one item'
            dispute_ids.add(t[0].id)

        super().load_dispute_infos(dispute_ids)

    def upload_group_key(self, check_contract_phase=True):
        if check_contract_phase:
            assert self.contract.dispute_confirmed()
        return self.contract.upload_group_key(
            self.master_bls_pk, transact={'from': self.account}
        )
