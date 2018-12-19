import math

import utils
import vss
from ethnode import EthNode

w3 = utils.connect()


def manipulate_share(node, sid):
    node.shares[sid - 1] += 1
    node.encrypted_shares = []
    for n, share in zip(node.nodes, node.shares):
        if n != node:
            shared_key = vss.shared_key(node.sk, n.pk)
            encrypted_share = vss.encrypt_share(share, n.id, shared_key)
            node.encrypted_shares.append(encrypted_share)


def run(num_nodes):
    contract = utils.deploy_contract('DKG')
    nodes = [EthNode(w3.eth.accounts[i]) for i in range(num_nodes)]

    tx_register = []
    tx_share_key = []
    tx_dispute = []
    tx_upload = None

    for i, node in enumerate(nodes):
        print(f'setting up node {i + 1}... ', end="", flush=True)
        c = utils.get_contract('DKG', contract.address)
        node.keygen()
        node.connect(c)
        print("done")
    print()

    for i, node in enumerate(nodes):
        print(f'registering node {i + 1}... ', end="", flush=True)
        tx = node.register()
        tx_register.append(tx)
        print("done")
    print()

    print(f'waiting for begin of key sharing phase... ', end='', flush=True)
    utils.mine_blocks_until(contract.registrations_confirmed)
    print('done\n')

    for i, node in enumerate(nodes):
        print(f'init secret sharing for node {i + 1}... ', end="", flush=True)
        node.init_secret_sharing()
        print("done")
    print()

    # invalid the share from last to first node
    # to actually also test the dispute case
    manipulate_share(nodes[-1], 1)

    for node in nodes:
        print(f'distribute key shares for node {node.id}... ', end="", flush=True)
        tx = node.share_key()
        tx_share_key.append(tx)
        print("done")
    print()

    print(f'waiting for begin of dispute phase... ', end='', flush=True)
    utils.mine_blocks_until(contract.sharing_confirmed)
    print('done\n')

    # for node in nodes:
    for node in nodes[:1]:
        print(f'loading and verififying shares for node {node.id}... ', end='', flush=True)
        try:
            node.load_shares()
        except ValueError:
            print("done (invalid share detected)")
        else:
            print("done")
    print()

    # for node in nodes:
    for node in nodes[:1]:
        dispute_ids = [n.id for n in node.nodes if hasattr(n, 'share') and not n.share_ok]
        for id in dispute_ids:
            print(f'submitting dispute from node {node.id} against node {id}... ', end="", flush=False)
            try:
                tx = node.dispute(id)
                tx_dispute.append(tx)
            except ValueError:
                print(f'done (dispute no required, node {id} already flagged as malicous)')
            else:
                print("done")
    print()

    print(f'waiting for begin of finalization phase... ', end='', flush=True)
    utils.mine_blocks_until(contract.dispute_confirmed)
    print('done\n')

    print(f'loading dispute and state information... ', end='', flush=True)
    nodes[0].verify_nodes()
    print("done\n")

    for node in nodes[0].nodes:
        t = 'OK' if node in nodes[0].group else 'FAILED'
        print(f'node {node.id}: status={t}')
    print()

    print(f'deriving master key... ', end='', flush=True)
    nodes[0].derive_group_keys()
    print("done")

    print(f'uploading master key... ', end='', flush=True)
    tx_upload = nodes[0].upload_group_key()
    print("done")

    print()
    print()
    print(f'GAS USAGE STATS FOR {num_nodes} NODES')
    print()
    print('                  |   min   |   max   |   avg')
    print('-----------------------------------------------')

    for txs, name in zip([tx_register, tx_share_key, tx_dispute], ['registration', 'key sharing', 'dispute']):
        gas_min = min(tx['gasUsed'] for tx in txs)
        gas_max = max(tx['gasUsed'] for tx in txs)
        gas_avg = math.ceil(sum(tx['gasUsed'] for tx in txs) / len(txs))
        print(f'{name:<17} | {gas_min:7} | {gas_max:7} | {gas_avg:7}')
        print('-----------------------------------------------')
    g = tx_upload['gasUsed']  # noqa
    print(f'master key upload | {g:7} | {g:7} | {g:7} ')
    print()
    print()
    print()
    print("=" * 80)
    print("=" * 80)
    print("=" * 80)
    print()
    print()
    print()


# see DKG.sol for setting of DELTA_INCLUDE if testing with a high number of nodes
# for n in [4, 8, 16, 32, 64, 128, 256]:
for n in [256]:
    run(n)
