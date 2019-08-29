import web3
import time
import threading
import hashlib
import os
import subprocess
import types

SOLC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "solc"))

CONTRACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "contracts"))
CONTRACTS_DIR_BIN = os.path.join(CONTRACTS_DIR, "bin")

w3 = None
_buffered_accounts = None

STATUS_OK = 1
STATUS_ERROR = 0

send_rpc_mine_block_commands = True


def connect(port=None, dev_mode=None):
    global w3, _buffered_accounts, send_rpc_mine_block_commands

    if port is None:
        ports = [7545, 8545]
    else:
        ports = port

    if w3 is None or not w3.isConnected():
        # large request timeout required for performance tests
        for p in ports:
            w3 = web3.Web3(
                web3.HTTPProvider(f"http://127.0.0.1:{p}", request_kwargs={"timeout": 60 * 10})
            )
            if w3.isConnected():
                if port is None:
                    send_rpc_mine_block_commands = p == 7545
                break
        _buffered_accounts = None

    if dev_mode:
        send_rpc_mine_block_commands = False

    assert w3.isConnected(), "Connecting to local Ethereum node failed!"
    return w3


def get_account_address(account_idx=-1):
    global _buffered_accounts
    connect()
    if not _buffered_accounts:
        _buffered_accounts = w3.eth.accounts
    return _buffered_accounts[account_idx]


def compile_contract(contract_name: str):
    return subprocess.check_output(
        [
            SOLC_PATH,
            "--abi",
            "--bin",
            "--optimize",
            "--overwrite",
            "--output-dir",
            CONTRACTS_DIR_BIN,
            os.path.join(CONTRACTS_DIR, contract_name + ".sol"),
        ]
    ).decode()


def load_contract(contract_name, str):
    with open(os.path.join(CONTRACTS_DIR_BIN, contract_name + ".bin"), "r") as f:
        contract_bin = f.read()
    with open(os.path.join(CONTRACTS_DIR_BIN, contract_name + ".abi"), "r") as f:
        contract_abi = f.read()
    return contract_abi, contract_bin


def deploy_contract(
    contract_name,
    deploying_account_address=None,
    gas=6_000_000,
    should_add_simplified_call_interfaces=True,
    return_tx_receipt=False,
):  # , patch_api=True, return_tx_receipt=False):
    """ Deploys the compiled contract (from the ethdkg/contracts/bin folder) and
        returns the contract instance.
    """
    connect()
    if deploying_account_address is None:
        deploying_account_address = w3.eth.accounts[-1]

    with open(os.path.join(CONTRACTS_DIR_BIN, contract_name + ".abi"), "r") as f_abi:
        with open(os.path.join(CONTRACTS_DIR_BIN, contract_name + ".bin"), "r") as f_bin:
            contract = w3.eth.contract(abi=f_abi.read(), bytecode=f_bin.read())

    tx_hash = contract.constructor().transact({"from": deploying_account_address, "gas": gas})
    mine_block()
    tx_receipt = wait_for_tx_receipt(tx_hash)
    contract = get_contract(
        contract_name, tx_receipt["contractAddress"], should_add_simplified_call_interfaces
    )
    if return_tx_receipt:
        return contract, tx_receipt
    return contract


def get_contract(contract_name, contract_address, should_add_simplified_call_interfaces=True):
    """ Gets the instance of an already deployed contract.
        if patch_api is set, all transactions are automatically syncronized, unless wait=False is specified in the tx
    """
    connect()
    with open(os.path.join(CONTRACTS_DIR_BIN, contract_name + ".abi"), "r") as f_abi:
        contract = w3.eth.contract(address=contract_address, abi=f_abi.read())

    if should_add_simplified_call_interfaces:
        add_simplified_call_interfaces(contract)

    return contract


def wait_for_tx_receipt(tx_hash):
    connect()
    return w3.eth.waitForTransactionReceipt(tx_hash)


def get_tx_receipt(tx_hash):
    connect()
    return w3.eth.getTransactionReceipt(tx_hash)


def wait_for_block(target_block_number):
    while block_number() < target_block_number:
        time.sleep(0.5)


class SimplifiedCallInterface:
    def __init__(self, contract, fn_name):
        self._func = getattr(contract.functions, fn_name)

    def __call__(self, *args, **kwargs):
        return SimplifiedCallInterfaceCall(self._func, *args, **kwargs)


class SimplifiedCallInterfaceCall:
    def __init__(self, _func, *args, **kwargs):
        self._func = _func
        self.args = args
        self.kwargs = kwargs

    def call_sync(self, caller_account_address=None):
        if caller_account_address is None:
            caller_account_address = get_account_address()
        tx_hash = self.call_async(caller_account_address)
        mine_block()
        return wait_for_tx_receipt(tx_hash)

    def call_async(self, caller_account_address=None):
        if caller_account_address is None:
            caller_account_address = get_account_address()
        tx_hash = self._func(*self.args, **self.kwargs).transact({"from": caller_account_address})
        return tx_hash

    def call(self, caller_account_address=None, sync=True):
        if sync:
            return self.call_sync(caller_account_address)
        return self.call_async(caller_account_address)


def add_simplified_call_interfaces(contract):
    fn_names = []
    for func in contract.all_functions():
        try:
            getattr(contract, func.fn_name)
            raise Exception("Cannot add simplyfied call interface due to naming conflict!")
        except AttributeError:
            fn_names.append(func.fn_name)

    for fn_name in fn_names:
        setattr(contract, fn_name, SimplifiedCallInterface(contract, fn_name))


def mine_block():
    connect()
    if send_rpc_mine_block_commands:
        w3.provider.make_request("evm_mine", params="")


def mine_blocks(num_blocks):
    if send_rpc_mine_block_commands:
        for i in range(num_blocks):
            mine_block()


def mine_blocks_until(predicate):
    if send_rpc_mine_block_commands:
        while not predicate():
            mine_block()


def block_number():
    connect()
    return w3.eth.blockNumber

