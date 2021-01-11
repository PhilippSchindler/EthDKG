import argparse
import os
import time
import sqlite3

from . import adversary
from . import logging
from . import utils
from .ethnode import EthNode, point_to_eth, point_G2_to_eth, get_db, init_db
from .utils import STATUS_OK, STATUS_ERROR
from .node import INVALID_SHARE
from web3.exceptions import BadFunctionCallOutput

node: EthNode
account: str
contract = None
logger = None
args = None
tx_receipt = None


def main():
    global account

    parse_cli_arguments()
    if(args.command != "init-db"):
        account = utils.get_account_address(args.account_index)

    if args.command == "deploy":
        deploy()
    elif args.command == "run":
        run()
        if args.save:
            node.save_public_info()

    elif args.command == 'init-db':
        init_db()


def parse_cli_arguments():
    global args
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_run = subparsers.add_parser("run", help="participate in the run of the DKG protocol")
    parser_run.add_argument(
        "contract_address", type=str, help="the address of the DKG smart contract to use"
    )

    parser_run.add_argument(
        "--save", default=False, help="save all the commitments and other info"
    )

    parser_run.add_argument(
        "--send-invalid-shares",
        type=str,
        help="testing only, used to send invalid shares to the specified node(s)",
        default=[],
        nargs="+",
    )
    parser_run.add_argument("--abort-on-key-share-submission", default=False, action="store_true")

    parser_deploy = subparsers.add_parser(
        "deploy", help="compiles and deploys the DKG smart contract"
    )

    parser_init_db = subparsers.add_parser(
        "init-db", help="initialize the database"
    )

    for subparser in [parser_init_db, parser_run, parser_deploy]:
        subparser.add_argument(
            "--account-index",
            type=int,
            default=0,
            help="the index of the ethereum account used to issue transactions (by default account 0 is used)",
        )
    

    args = parser.parse_args()
    if args.command == "run":
        for i in range(len(args.send_invalid_shares)):
            try:
                args.send_invalid_shares[i] = int(args.send_invalid_shares[i])
            except ValueError:
                # this is okay, receiver is specified via address instead
                pass


def deploy():
    global logger, contract
    logger = logging.create_logger("deployment.log")
    logger.info("compiling contract (ETHDKG.sol)...")
    compiler_output = utils.compile_contract("ETHDKG")
    logger.info("contract compiled successfully")
    logger.debug(compiler_output)

    logger.info("deploying contract...")
    contract, tx_receipt = utils.deploy_contract("ETHDKG", account, return_tx_receipt=True)
    logger.info("contract deployed")

    logger.newline()
    logger.info(f"contract address: {contract.address}")
    logger.info(f"deployed by:      {tx_receipt['from']}")
    log_tx_receipt(tx_receipt)


def run():
    global logger
    logger = logging.create_logger(f"node.{args.account_index}.log")
    init()
    registration()
    share_distribution()
    share_verification()
    dispute_submission()
    dispute_verification()
    key_derivation_submission()
    key_derivation_verification()
    key_derivation_recovery()
    key_derivation_result()

    node.save_private_info()


def init():
    global node, contract
    print()
    logger.info("started ETHDKG protocol client")
    logger.info(f"account index:   {args.account_index}")
    logger.info(f"account address: {account}")
    logger.newline(3)

    logger.info("INITIALIZATION PHASE")
    logger.newline()
    logger.info("connecting to ETHDKG contract")
    contract = utils.get_contract("ETHDKG", args.contract_address)
    logger.info(f"contract address: {contract.address}")
    try:
        contract.caller.num_nodes()
    except BadFunctionCallOutput as e:
        logger.critical("failed to connect to contract (is contract deployed?)")
        logger.newline(3)
        raise e

    node_cls = EthNode
    kwargs = {}

    if args.send_invalid_shares:
        node_cls = adversary.Adversary_SendInvalidShares
        kwargs["targets"] = args.send_invalid_shares
    elif args.abort_on_key_share_submission:
        node_cls = adversary.Adversary_AbortOnKeyShareSubmission

    node = node_cls(account, contract, logger, **kwargs)

    logger.newline()
    logger.info("initialization completed")

    if type(node) != EthNode:
        logger.newline()
        logger.critical(f"RUNNING AN ADVERSARIAL NODE {type(node)}")

    logger.newline(3)


def registration():
    global tx_receipt

    logger.info(f"REGISTRATION PHASE")
    logger.newline()

    current_block_number = utils.block_number()
    logger.info(f"current block: {current_block_number}")
    logger.info(f"registration until block: {node.T_REGISTRATION_END}")
    logger.newline()
    if current_block_number > node.T_REGISTRATION_END:
        logger.critical("REGISTRATION FAILED (late registration)")
        exit(1)

    logger.info("generating key pair")
    logger.info(f"private key: {node.secret_key}")
    logger.info(f"public key:  {node.public_key}")
    logger.newline()

    logger.info("sending registration transaction")
    log_tx(node.register())

    logger.info("waiting for end of registration phase and consensus stabilization")
    wait_until(node.T_REGISTRATION_END + node.DELTA_CONFIRM)
    logger.newline()
    logger.info("registration phase completed")
    logger.newline()

    node.setup()
    logger.info(f"registered nodes (n): {node.n}")
    logger.info(f"threshold (t):        {node.t}")
    logger.info("registered nodes: (* marks this node)")
    for idx, pk in node.public_keys.items():
        addr = node.addresses[idx]
        s = " "
        if account == addr:
            s = "*"
        logger.info(f"    {addr}{s}  public key: {pk}")
    logger.newline(3)


def share_distribution():
    logger.info(f"SHARE DISTRIBUTION PHASE")
    logger.newline()

    current_block_number = utils.block_number()
    logger.info(f"current block: {current_block_number}")
    logger.info(f"share distribution until block: {node.T_SHARE_DISTRIBUTION_END}")
    logger.newline()
    if current_block_number > node.T_SHARE_DISTRIBUTION_END:
        logger.critical("SHARE DISTRIBUTION FAILED (late distribution)")
        exit(1)

    logger.info(f"running ({node.t}, {node.n}) secret sharing protocol")
    logger.info(f"shared secret:    {node.secret}")
    tx_hash = node.distribute_shares()
    logger.newline()

    logger.info("sending share distribution transaction")
    log_tx(tx_hash)
    logger.newline()

    logger.info("waiting for end of share distribution phase and consensus stabilization")
    wait_until(node.T_SHARE_DISTRIBUTION_END + node.DELTA_CONFIRM)
    logger.newline()
    logger.info("share distribution phase completed")
    logger.newline()


def share_verification():
    logger.info("loading shares")
    logger.newline()
    node.load_shares()

    missing, invalid, ok = 0, 0, 0
    for other_node in node.other_nodes:
        addr = node.addresses[other_node]
        if other_node not in node.decrypted_shares:
            logger.warning(f"node {addr}: NO share received")
            missing += 1
        elif node.decrypted_shares[other_node] == INVALID_SHARE:
            logger.error(f"node {addr}: INVALID share received")
            invalid += 1
        else:
            logger.info(f"node {addr}: valid share received")
            logger.info(f"    share for this node: {node.decrypted_shares[other_node]}")
            logger.info(f"    encrypted shares:    {node.encrypted_shares[other_node]}")
            logger.info(f"    commitments:         {node.commitments[other_node]}")
            ok += 1
        logger.newline()

    logfunc = logger.error if invalid > 0 else (logger.warning if missing > 0 else logger.info)
    logfunc(f"shares received: {ok} ok, {missing} missing, {invalid} invalid")
    if missing + invalid > node.t:
        logger.critical("insufficient valid shares received")
        exit(1)

    logger.newline(3)


def dispute_submission():
    logger.info(f"DISPUTE PHASE")
    logger.newline()
    current_block_number = utils.block_number()
    logger.info(f"current block: {current_block_number}")
    logger.info(f"dispute phase until block: {node.T_DISPUTE_END}")
    logger.newline()

    disputes = node.compute_disputes()
    if not disputes:
        logger.info("no disputes to submit")
        return
    if current_block_number > node.T_DISPUTE_END:
        logger.critical("DISPUTE FAILED (phase has already ended)")
        exit(1)

    logger.info(f"submitting disputes against {len(disputes)} node(s)")
    txs = node.submit_disputes(disputes)

    logger.newline()
    logger.info("submitting transactions")
    logger.info("transaction hashes:")
    for tx_hash in txs.values():
        logger.info(f"    {tx_hash.hex()}")

    for issuer, tx_hash in txs.items():
        logger.newline()
        print(f"dispute against node {node.addresses[issuer]}")
        log_tx(tx_hash)

    logger.info("all disputes submitted")


def dispute_verification():
    logger.newline()
    logger.info("waiting for end of share dispute phase and consensus stabilization")
    wait_until(node.T_DISPUTE_END + node.DELTA_CONFIRM)
    logger.newline()
    logger.info("dispute phase completed")
    logger.newline()
    logger.info("loading received disputes")

    node.load_disputes()
    logger.newline(3)


def key_derivation_submission():
    logger.info(f"KEY DERIVATION PHASE")
    logger.newline()
    current_block_number = utils.block_number()
    logger.info(f"current block: {current_block_number}")
    logger.newline()
    logger.info("deriving set of qualified nodes")
    node.compute_qualified_nodes()
    logger.info("nodes status: (* marks this node)")
    qualified, adversarial, failed = 0, 0, 0
    for idx, addr in node.addresses.items():
        submitted = idx in node.encrypted_shares
        disputed = idx in node.disputed_nodes
        s = "*:" if account == addr else ": "
        if submitted and not disputed:
            logger.info(f"    {addr}{s} qualified")
            qualified += 1
        elif submitted:
            logger.info(f"    {addr}{s} adversarial")
            adversarial += 1
        else:
            logger.info(f"    {addr}{s} failed")
            failed += 1
    logger.newline()

    logfunc = logger.error if adversarial > 0 else (logger.warning if failed > 0 else logger.info)
    logfunc(f"status summary: {qualified} qualified, {failed} failed, {adversarial} adversarial")
    if failed + adversarial > node.t:
        logger.critical("insufficient qualified nodes remaining")
        exit(1)

    logger.newline()
    logger.info("deriving key share")
    tx = node.submit_key_share()
    logger.newline()
    logger.info("submitting transaction")
    log_tx(tx)


def key_derivation_verification():
    logger.newline()
    logger.info("waiting for end of key submission and consensus stabilization")
    wait_until(node.T_KEY_SHARE_SUBMISSION_END + node.DELTA_CONFIRM)
    logger.newline()
    logger.info("key submission completed")
    logger.newline()
    logger.info("loading key shares")
    node.load_key_shares()


def key_derivation_recovery():
    if len(node.key_shares) == len(node.qualified_nodes):
        logger.info("no need to recover any key shares")
        return
    logger.newline()
    logger.info(
        f"initiating recovery process for "
        f"{len(node.qualified_nodes) - len(node.key_shares)} node(s)"
    )
    logger.newline()
    log_tx(node.recover_key_shares())
    logger.info("waiting for shares to recover all missing key shares")
    logger.newline()
    node.load_recovered_key_shares()

    logger.info("submitting recovered key shares")
    txs = node.submit_recovered_key_shares()
    logger.newline()
    logger.info("submitting transactions")
    logger.info("transaction hashes:")
    for tx_hash in txs.values():
        logger.info(f"    {tx_hash.hex()}")

    for issuer, tx_hash in txs.items():
        logger.newline()
        logger.info(f"recovered key share for node {node.addresses[issuer]}")
        log_tx(tx_hash)

    logger.info("all recovered key shares submitted")


def key_derivation_result():
    logger.info("deriving master public key")
    log_tx(node.submit_master_public_key(), may_fail=True)
    node.derive_group_keys()

    logger.newline(3)
    logger.info("DKG protocol completed")
    logger.newline()
    logger.info(f"master public key: {point_G2_to_eth(node.master_public_key)}")
    logger.newline()
    logger.info(f"group secret key (this node): {node.group_secret_key}")
    logger.info(f"group public key (this node): {point_G2_to_eth(node.group_public_key)}")
    logger.info(
        f"correctness proof for group public key: "
        + str((point_to_eth(node.group_public_key_in_G1), node.group_public_key_correctness_proof))
    )
    logger.newline()


def log_tx(tx_hash, may_fail=False):
    logger.info(f"transaction hash: {tx_hash.hex()}")
    logger.newline()
    logger.info("waiting for confirmation")
    logger.newline()
    tx_receipt = utils.wait_for_tx_receipt(tx_hash)
    log_tx_receipt(tx_receipt, may_fail=False)


def log_tx_receipt(receipt, may_fail=False):
    global tx_receipt
    tx_receipt = receipt
    logger.info("transaction confirmed")

    status_to_name = {STATUS_OK: "OK", STATUS_ERROR: "FAILED"}
    logger.info(f"transaction hash: {tx_receipt.transactionHash.hex()}")
    logger.info(f"block number:     {tx_receipt.blockNumber}")
    logger.info(f"consumed gas:     {tx_receipt.gasUsed}")
    logger.info(f"status:           {status_to_name[tx_receipt.status]} ({tx_receipt.status})")
    logger.newline()

    if tx_receipt.status != STATUS_OK and not may_fail:
        logger.critical("transaction failed, see ethereum node / ganache for error details")
        exit(1)


def wait_until(block_number):
    prev = None
    while True:
        current = utils.block_number()
        if current != prev:
            remaining = block_number - current
            if remaining <= 0:
                return
            logger.info(f"current block: {current}; {remaining} blocks remaining")
            prev = current
        time.sleep(1.0)


main()
