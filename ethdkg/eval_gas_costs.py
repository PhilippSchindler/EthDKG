import time
import math
import collections

from .node import Node, INVALID_SHARE
from .ethnode import EthNode, point_to_eth, point_G2_to_eth, point_from_eth, point_G2_from_eth
from .adversary import Adversary_SendInvalidShares
from . import utils
from .utils import STATUS_OK, STATUS_ERROR

# contract deployment:      3125616
# registration
# sharing:                  1495419
# dispute
# key derivation
#   - submit key share
#   - recover key share
#   - upload master key

contract = None
nodes = None
stats = None
num_nodes = None


def print_stats(name, label, txs, min_for_duplicate=False):
    gas_min = min(tx.gasUsed for tx in txs)
    gas_max = max(tx.gasUsed for tx in txs)
    gas_total = sum(tx.gasUsed for tx in txs)
    gas_avg = math.ceil(gas_total / len(txs))
    c = collections.Counter([tx.gasUsed for tx in txs])
    print()
    print(f"{label} (n={len(nodes)})")
    print(f"min: {gas_min}, avg: {gas_avg}, max: {gas_max}, total: {gas_total}")
    print(c)
    print([tx.gasUsed for tx in txs])
    print()
    stats[name].append(gas_max)
    if min_for_duplicate:
        stats[name + ", duplicate"].append(gas_min)


def init(n=5):
    global contract, nodes, num_nodes
    num_nodes = n

    utils.compile_contract("ETHDKG")
    contract = utils.deploy_contract("ETHDKG")

    print(f"contract deployed at: {contract.address}")
    assert contract.caller.DELTA_INCLUDE() > n

    print(f"initializing nodes (0/{n})...")

    nodes = []
    for i in range(n - 1):
        nodes.append(EthNode(utils.get_account_address(i), contract))
        print_replace(f"initializing nodes ({i+1}/{n})...")

    # last node sends invalid shares
    nodes.append(
        Adversary_SendInvalidShares(
            utils.get_account_address(n - 1), contract, targets=[node.address for node in nodes[:3]]
        )
    )
    print_replace(f"initializing nodes ({n}/{n})...")

    for node in nodes[3:]:
        node._disable_share_verification = True

    for node in nodes:
        node._disable_dispute_verification = True
        node._disable_key_share_verification = True
        node._disable_recovery_share_verification = True


def print_replace(text):
    print(f"\033[F{text}")


def registration(batch_size=25):
    print(f"running registration (0/{len(nodes)})...")

    txs = []
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i : i + batch_size]
        batch_txs = [node.register(sync=False) for node in batch]
        time.sleep(1)
        utils.mine_block()
        batch_tx_receipts = [utils.get_tx_receipt(tx) for tx in batch_txs]
        assert None not in batch_tx_receipts
        txs += batch_tx_receipts
        print_replace(f"running registration ({i + len(batch)}/{len(nodes)})...")

    print_stats("registration", f"gas consumption for registration transaction", txs)
    utils.mine_until_registrations_confirmed(contract)


def setup():
    print(f"running setup (0/{len(nodes)})...")

    n = len(nodes)
    t = math.ceil(n / 2) - 1

    addresses = [contract.caller.addresses(i) for i in range(n)]
    public_keys = {
        int(addr, 16): point_from_eth((contract.caller.public_keys(addr, 0), contract.caller.public_keys(addr, 1)))
        for addr in addresses
    }
    addresses = {int(addr, 16): addr for addr in addresses}

    for i, node in enumerate(nodes):
        node.n = n
        node.t = t
        node.addresses = addresses
        idx = int(node.address, 16)
        super(EthNode, node).setup(n, t, idx, public_keys)
        print_replace(f"running setup ({i+1}/{len(nodes)})...")


def share_distribution():
    global nodes

    txs = []
    print(f"running share distribution (0/{len(nodes)})...")
    for i, node in enumerate(nodes):
        tx_receipt = node.distribute_shares(sync=True)
        assert tx_receipt.status == STATUS_OK
        txs.append(tx_receipt)
        print_replace(f"running share distribution ({i + 1}/{len(nodes)})...")

    print_stats("share distribution", f"gas consumption for sharing transaction", txs)
    utils.mine_until_share_distribution_confirmed(contract)

    print(f"processing incomming shares (0/{len(nodes)})...")
    events = contract.events.ShareDistribution.createFilter(fromBlock=0).get_all_entries()
    for i, e in enumerate(events):
        issuer = int(e.args.issuer, 16)
        receivers = (node for node in nodes[0].nodes if node != issuer)
        encrypted_shares = dict(zip(receivers, e.args.encrypted_shares))
        commitments = [point_from_eth(p) for p in e.args.commitments]
        for node in nodes:
            if issuer == node.idx:
                continue
            super(EthNode, node).load_shares(issuer, encrypted_shares, commitments)
        print_replace(f"processing incomming shares ({i + 1}/{len(nodes)})...")

    assert nodes[0].decrypted_shares[nodes[-1].idx] == INVALID_SHARE
    nodes = nodes[:-1]
    print(f"\nstopping adversary node which sent invalid shares, {len(nodes)} nodes remaining\n")


def disputes(batch_size=1):
    txs = []
    print(f"running disputes (0/{len(nodes)})...")
    for i, node in enumerate(nodes):
        tx_receipts = list(node.submit_disputes(sync=True).values())
        for tx_receipt in tx_receipts:
            assert tx_receipt.status == STATUS_OK
        txs += tx_receipts
        print_replace(f"running disputes ({i + 1}/{len(nodes)})...")

    print_stats("dispute", f"gas consumption for dispute transaction", txs)
    utils.mine_until_disputes_confirmed(contract)

    for tx_receipt in txs:
        assert tx_receipt.status == STATUS_OK

    events = contract.events.Dispute.createFilter(fromBlock=0).get_all_entries()
    print(f"processing incomming disputes (0/{len(events)})...")
    for i, e in enumerate(events):
        issuer_idx = int(e.args.issuer, 16)
        disputer_idx = int(e.args.disputer, 16)
        shared_key = point_from_eth(e.args.shared_key)
        shared_key_correctness_proof = e.args.shared_key_correctness_proof
        for node in nodes:
            node.load_dispute(issuer_idx, disputer_idx, shared_key, shared_key_correctness_proof)
        print_replace(f"processing incomming disputes ({i + 1}/{len(events)})...")


def key_derivation(stop_max=False):
    global nodes

    if stop_max:
        nodes = nodes[: num_nodes // 2 + 1]
    else:
        nodes = nodes[:-1]
    print(f"\nstopping adversary node(s) which do not publish their key shares, {len(nodes)} nodes remaining\n")

    txs = []
    print(f"running key share submission (0/{len(nodes)})...")
    for i, node in enumerate(nodes):
        node.compute_qualified_nodes()
        tx_receipt = node.submit_key_share(sync=True)
        assert tx_receipt.status == STATUS_OK
        txs.append(tx_receipt)
        print_replace(f"running key share submission ({i + 1}/{len(nodes)})...")

    print_stats("key share submission", f"gas consumption for key share submission", txs)
    utils.mine_until_key_share_submission_confirmed(contract)

    events = contract.events.KeyShareSubmission.createFilter(fromBlock=0).get_all_entries()
    print(f"processing incomming key share submission (0/{len(events)})...")
    for i, e in enumerate(events):
        issuer = int(e.args.issuer, 16)
        key_share_G1 = point_from_eth(e.args.key_share_G1)
        key_share_G2 = point_G2_from_eth(e.args.key_share_G2)
        for node in nodes:
            super(EthNode, node).load_key_share(
                issuer, key_share_G1, e.args.key_share_G1_correctness_proof, key_share_G2
            )
        print_replace(f"processing incomming key share submission ({i + 1}/{len(events)})...")


def key_derivation_recovery():
    txs = []
    print(f"running key share recovery (0/{len(nodes)})...")
    for i, node in enumerate(nodes):
        tx_receipt = node.recover_key_shares(sync=True)
        assert tx_receipt.status == STATUS_OK
        txs.append(tx_receipt)
        print_replace(f"running key share recovery ({i + 1}/{len(nodes)})...")

    print_stats("key share recovery", f"gas consumption for key share recovery", txs)

    print("loading and executing eventual key share recovery...")
    nodes[0].load_recovered_key_shares()
    nodes[1].load_recovered_key_shares()
    txs0 = nodes[0].submit_recovered_key_shares(sync=True)
    txs1 = nodes[1].submit_recovered_key_shares(sync=True)

    print()
    for tx0 in txs0.values():
        print("gas costs for submission of recovered key share: ", tx0.gasUsed)
        stats["recovered key share submission"].append(tx0.gasUsed)
    for tx1 in txs1.values():
        print("gas costs for submission of recovered key share: ", tx1.gasUsed)
        stats["recovered key share submission, duplicate"].append(tx1.gasUsed)
    print()

    tx0 = nodes[0].submit_master_public_key(sync=True)
    tx1 = nodes[1].submit_master_public_key(sync=True)
    print("gas costs for submission of master key: ", tx0.gasUsed)
    print("gas costs for submission of master key: ", tx1.gasUsed)
    stats["master key submission"].append(tx0.gasUsed)
    stats["master key submission, duplicate"].append(tx1.gasUsed)


def run(n=5, stop_max=False):
    global stats
    if stats is None:
        stats = collections.defaultdict(list)

    print(f"\n\n{'='*80}\nRUNNING EVALUATION FOR N={n}\n")
    init(n)
    registration()
    setup()
    share_distribution()
    disputes()
    key_derivation(stop_max=stop_max)
    key_derivation_recovery()

    print("=" * 80)
    print()
    print(stats)
    print()
    print("=" * 80)
    print()


def run_all(N=[8, 16, 32, 64, 128, 192, 256, 384, 512], stop_max=True):

    for n in N:
        run(n, stop_max)

    print("=" * 80)
    print("=" * 80)
    print()
    print(N)
    print(stats)

