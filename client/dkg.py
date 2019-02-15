import argparse
import logging
import time
import sys

import utils
import vss
from ethnode import EthNode
from constants import *


# logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s   %(message)s')
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

account = None
contract = None
node = None
w3 = None
args = None


def main():
    global args, node, contract, account, w3

    args = parse_cli_arguments()
    # print(args)

    logging._info = logging.info
    if args.verbose:
        logging.info = default_logging_info
    else:
        logging.info = trimmed_logging_info

    w3 = utils.connect()
    if args.node_idx < -1 or args.node_idx >= len(w3.eth.accounts):
        logging.error(
            'invalid node-idx specified, check that the specified account is available in Ganache'
        )

    account = w3.eth.accounts[args.node_idx]

    if args.cmd == 'deploy':
        deploy()

    elif args.cmd == 'run':
        w3 = utils.connect()
        contract = utils.get_contract('DKG', args.contract)
        node = EthNode(account)
        node.connect(contract)
        run()


def parse_cli_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--verbose', action='store_true', help='do not trim log messages'
    )
    parser.add_argument(
        '--line-length',
        type=int,
        default=80,
        help='sets the maximum cli line length, ignored if verbose is specified',
    )

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    parser_deploy = subparsers.add_parser(
        'deploy', help='deploy the DKG smart contract'
    )
    parser_deploy.add_argument(
        'node_idx',
        nargs='?',
        type=int,
        default=-1,
        help='index of the Ethereum account to use',
    )

    parser_run = subparsers.add_parser(
        'run', help='run the DKG client software to participate in the DKG protocol'
    )
    parser_run.add_argument(
        'node_idx', type=int, help='index of the Ethereum account to use'
    )
    parser_run.add_argument('contract', type=str, help='address of the DKG contract')
    parser_run.add_argument(
        '--send-invalid-shares',
        metavar='NODE_ID(s)',
        type=int,
        nargs='+',
        help='for testing only, sends invalid share(s) to the given node(s)',
    )
    parser_run.add_argument(
        '--abort-after-registration',
        action='store_true',
        help='for testing only, abort client after registration phase',
    )
    parser_run.add_argument(
        '--skip-master-key',
        action='store_true',
        help='if specified, the master public key is not automatically sent to the smart contract'
    )

    return parser.parse_args()


def default_logging_info(msg='', *args, **kwargs):
    return logging._info(msg, *args, **kwargs)


def trimmed_logging_info(msg=''):
    if len(msg) > args.line_length:
        msg = msg[: args.line_length - 3]
        msg += '...'
    logging._info(msg)


def deploy():
    logging.info(f'deploying DKG contract from Ethereum account {account}...')
    logging.info()
    contract, tx = utils.deploy_contract('DKG', account, return_tx_receipt=True)
    log_tx(tx, 'deployment transaction confirmed:')
    logging.info(f'contract deployed at: {contract.address}')


def run():
    logging.info()
    logging.info('RUNNING DKG CLIENT')
    logging.info(f'    NODE ACCOUNT ADDRESS: {account}')
    logging.info(f'    CONTRACT ADDRESS:     {contract.address}')
    logging.info()

    T_SHARING_START = contract.T_REGISTRATION_END() + contract.DELTA_CONFIRM()
    T_DISPUTE_START = contract.T_SHARING_END() + contract.DELTA_CONFIRM()
    T_FINALIZATION_START = contract.T_DISPUTE_END() + contract.DELTA_CONFIRM()

    register()
    wait_for(
        EVENT_REGISTRATION,
        target_block_number=T_SHARING_START,
        target_description='key sharing phase',
    )

    if args.abort_after_registration:
        logging.info('ABORTING PROTOCOL')
        return

    share_key()
    wait_for(
        EVENT_KEY_SHARING,
        target_block_number=T_DISPUTE_START,
        target_description='dispute phase',
    )
    key_sharing_stats()

    dispute()
    wait_for(
        EVENT_DISPUTE_SUCCESSFUL,
        target_block_number=T_FINALIZATION_START,
        target_description='finalization phase',
    )

    final_stats()
    derive_keys()
    upload_master_key()


def register():
    logging.info('generating keypair')
    node.keygen()
    logging.info(f'    sk:     {node.sk}')
    logging.info(f'    pk:     {node.pk}')
    logging.info(f'    bls_pk: {node.bls_pk}')
    logging.info()

    logging.info('REGISTRATION PHASE STARTED')
    logging.info()

    if not contract.in_registration_phase():
        logging.error('aborting! contract not in registration phase')
        return

    logging.info('sending registration transaction...')

    tx = node.register()
    log_tx(tx, 'registration transaction confirmed')


def share_key():
    logging.info('KEY SHARING PHASE STARTED')
    logging.info()
    node.init_secret_sharing()

    logging.info(f'loading registration data...')
    logging.info(f'    assigned id for this node:            {node.id}')
    logging.info(f'    number of register nodes (n):         {node.n}')
    logging.info(f'    signing / key recovery threshold (t): {node.t}')
    logging.info()

    logging.info('generating key shares...')
    for n, s in zip(node.nodes, node.shares):
        logging.info(f'    node {n.id}: {s}')
    logging.info()

    if args.send_invalid_shares is not None:
        sids = args.send_invalid_shares
        logging.info()
        for sid in sids:
            logging.info(f'MANIPULATING SHARE FOR NODE WITH ID {sid}')
            node.shares[sid - 1] += 1
        logging.info()
        node.encrypted_shares = []
        for n, share in zip(node.nodes, node.shares):
            if n != node:
                shared_key = vss.shared_key(node.sk, n.pk)
                encrypted_share = vss.encrypt_share(share, n.id, shared_key)
                node.encrypted_shares.append(encrypted_share)

    logging.info('encrypting key shares...')
    j = 0
    for n in node.nodes:
        if n.id == node.id:
            logging.info(f'    node {n.id}: <no encrypted share for oneself>')
        else:
            logging.info(f'    node {n.id}: {node.shares[j]}')
            j += 1
    logging.info()

    logging.info('sending key sharing transaction...')
    tx = node.share_key()
    log_tx(tx, 'key sharing transaction confirmed')


def key_sharing_stats():
    logging.info('decrypting received shares...')
    logging.info()
    logging.info('verifying received shares...')
    try:
        node.load_shares()
    except ValueError:
        logging.info('INVALID SHARES RECEIVED:')
    else:
        logging.info('all received shares are valid:')

    for n in node.nodes:
        if n == node:
            logging.info(f'    node {n.id}: this node')
            logging.info(f'        share: {n.share}')
        else:
            if hasattr(n, 'share'):
                vvalid = 'valid' if n.coefficients_ok else 'INVALID'
                svalid = 'valid' if n.share_ok else 'INVALID'
                logging.info(f'    node {n.id}: ')
                logging.info(f'        {svalid} share: {n.share}')
                logging.info(f'        verification vector {vvalid}')
            else:
                logging.info(f'    node {n.id}: <no share received>')
    logging.info()


def dispute():
    logging.info('DISPUTE PHASE STARTED')
    dispute_ids = [n.id for n in node.nodes if hasattr(n, 'share') and not n.share_ok]
    if len(dispute_ids) == 0:
        logging.info()
        logging.info('no disputes to submit')
    else:
        for id in dispute_ids:
            logging.info()
            logging.info(f'submitting dispute for node {id}')
            try:
                tx = node.dispute(id)
                log_tx(tx, 'dispute transaction confirmed')
            except ValueError:
                logging.info(f'dispute no required, node {id} already flagged as malicous')
                logging.info()
        logging.info('no more dispute to file')
    logging.info()


def wait_for(event_type, target_block_number, target_description):
    logging.info(
        f'waiting for {event_type} events until {target_description} starts...'
    )

    events = []
    num_events = 0
    last_checked = None

    while True:
        t = w3.eth.blockNumber
        if t == last_checked:
            time.sleep(1)
            continue
        last_checked = t

        events = utils.get_events(contract, event_type)
        new_events = events[num_events:]
        log_events(new_events)
        num_events = len(events)
        if new_events:
            logging.info()

        if t >= target_block_number:
            break
        logging.info(
            f'waiting for {target_block_number - t} blocks until {target_description} starts...'
        )
    logging.info()


def final_stats():
    logging.info('FINALIZATION PHASE STARTED')
    logging.info()
    logging.info('checking which nodes should contribute to the master key')
    try:
        node.verify_nodes()
        error = False
    except RuntimeError:
        error = True

    for n in node.nodes:
        t = 'YES' if n in node.group else 'NO'
        logging.info(f'    node {n.id}: {t}')
    logging.info()

    if error:
        logging.info('NOT ENOUGH NODES SHARED THEIR KEYS SUCCESSFULLY')
        logging.info('ABORTING PROTOCOL')
        # TODO send abort transaction to return deposit
        sys.exit(1)


def derive_keys():
    logging.info('deriving group and master key...')
    node.derive_group_keys()
    logging.info(f'    BLS group secret key for this node: {node.group_sk}')
    logging.info(f'    BLS group public key for this node: {node.group_bls_pk}')
    logging.info(f'    BLS master public key:              {node.master_bls_pk}')
    logging.info()


def upload_master_key():
    if args.skip_master_key:
        logging.info('skipping to send BLS master public key to contract')
        logging.info()
        return

    logging.info('sending BLS master public key to contract...')
    try:
        tx = node.upload_group_key()
        log_tx(tx, 'transaction confirmed')
    except ValueError:
        logging.info('sending not required, already published by a different node')
    logging.info()


def log_tx(tx, info):
    logging.info(f'{info}')
    logging.info(f'    transaction hash: {tx["transactionHash"].hex()}')
    logging.info(f'    block number:     {tx["blockNumber"]}')
    logging.info(f'    gas used:         {tx["gasUsed"]}')
    logging.info()


def log_events(events):
    for e in events:
        log_event(e)


def log_event(e):
    logging.info()
    logging.info(f'{e.event} event received')

    args = e.args
    if e.event == EVENT_REGISTRATION:
        logging.info(f'    block number: {e.blockNumber}')
        logging.info(f'    assigned id:  {args["id"]}')
        logging.info(f'    address:      {args["node_adr"]}')
        logging.info(f'    pk:           {args["pk"]}')
        logging.info(f'    bls_pk:       {args["bls_pk"]}')

    elif e.event == EVENT_KEY_SHARING:
        logging.info(f'    block number:        {e.blockNumber}')
        logging.info(f'    issuing node id:     {args["issuer"]}')
        logging.info(f'    encrypted_shares:    {args["encrypted_shares"]}')
        logging.info(f'    verification vector: {args["public_coefficients"]}')

    elif e.event == EVENT_DISPUTE_SUCCESSFUL:
        disputed_node = [n for n in node.nodes if n.account == args['bad_issuer_addr']][
            0
        ]
        logging.info(f'    block number:          {e.blockNumber}')
        logging.info(f'    disputed node id:      {disputed_node.id}')
        logging.info(f'    disputed node address: {disputed_node.account}')

    else:
        assert False, 'not implemented'


if __name__ == '__main__':
    main()
