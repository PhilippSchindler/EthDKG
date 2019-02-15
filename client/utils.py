import web3
import solc
import time
import threading
import hashlib
import os

w3 = None
cache = {}


def connect():
    global w3
    if w3 is None or not w3.isConnected:
        # large request timeout require for performance tests
        w3 = web3.Web3(web3.HTTPProvider('http://127.0.0.1:8545', request_kwargs={'timeout': 60 * 10}))
    assert w3.isConnected
    return w3


def filehash(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def compile_contract(contract_name):
    """ compiles the given contract (from the ./contracts folder)
        and returns its ABI interface
    """

    path = os.getcwd()
    if path.endswith('client'):
        path = f'../contracts/{contract_name}.sol'
    else:
        path = f'./contracts/{contract_name}.sol'

    h = filehash(path)

    interface = cache.get(h)
    if interface:
        return interface

    with open(path) as f:
        src = f.read()
    for i in solc.compile_source(src, optimize=True).values():
        interface = i
        break

    cache[h] = interface
    return interface


def get_contract(contract_name, contract_address, patch_api=True):
    """ gets the instance of an already deployed contract
        if patch_api is set, all transactions are automatically syncronized, unless wait=False is specified in the tx
    """
    connect()

    interface = compile_contract(contract_name)
    instance = w3.eth.contract(
        address=contract_address,
        abi=interface['abi'],
        ContractFactoryClass=web3.contract.ConciseContract,
    )
    if patch_api:
        for name, func in instance.__dict__.items():
            if isinstance(func, web3.contract.ConciseMethod):
                instance.__dict__[name] = _tx_executor(func)

    # add event handling stuff to the instance object
    contract = w3.eth.contract(abi=interface['abi'], bytecode=interface['bin'])
    instance.eventFilter = contract.eventFilter
    instance.events = contract.events
    return instance


def _tx_executor(contract_function):
    """ modifies the contract instance interface function such that whenever a transaction is performed
        it automatically waits until the transaction in included in the blockchain
        (unless wait=False is specified, in the case the default the api acts as usual)
    """

    def f(*args, **kwargs):
        wait = kwargs.pop('wait', True)
        if 'transact' in kwargs and wait:
            tx_hash = contract_function(*args, **kwargs)
            tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
            return tx_receipt
        return contract_function(*args, **kwargs)

    return f


def deploy_contract(
    contract_name, account=None, patch_api=True, return_tx_receipt=False
):
    """ compiles and deploy the given contract (from the ./contracts folder)
        returns the contract instance
    """
    connect()
    if account is None:
        account = w3.eth.accounts[-1]

    interface = compile_contract(contract_name)
    contract = w3.eth.contract(abi=interface['abi'], bytecode=interface['bin'])

    # increase max gas t
    # tx_hash = contract.constructor().transact({'from': account, 'gas': 7_500_000})

    tx_hash = contract.constructor().transact({'from': account, 'gas': 5_000_000})
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    c = get_contract(contract_name, tx_receipt['contractAddress'], patch_api)
    if return_tx_receipt:
        return c, tx_receipt
    return c


def flatten(list_of_lists):
    return [y for x in list_of_lists for y in x]


def get_events(contract_instance, event_name, from_block=0, to_block=None):
    # eventFilter = contract.eventFilter(event_name, {'fromBlock': 0})
    eventFilter = contract_instance.events.__dict__[event_name].createFilter(
        fromBlock=from_block, toBlock=to_block
    )
    return [
        e
        for e in eventFilter.get_all_entries()
        if e.address == contract_instance.address
    ]


def wait_for(predicate, check_interval=1.0):
    while not predicate():
        time.sleep(check_interval)


def mine_block():
    connect()
    w3.providers[0].make_request('evm_mine', params='')


def mine_blocks(num_blocks):
    for i in range(num_blocks):
        mine_block()


def mine_blocks_until(predicate):
    while not predicate():
        mine_block()

def blockNumber():
    connect()
    return w3.eth.blockNumber


def run(func_or_funcs, args=()):
    """ executes the given functions in parallel and waits
        until all execution have finished
    """
    threads = []
    if isinstance(func_or_funcs, list):
        funcs = func_or_funcs
        for i, f in enumerate(funcs):
            arg = args[i] if isinstance(args, list) else args
            if (arg is not None) and (not isinstance(arg, tuple)):
                arg = (arg,)
            threads.append(threading.Thread(target=f, args=arg))
    else:
        func = func_or_funcs
        assert isinstance(args, list)
        for arg in args:
            xarg = arg if isinstance(arg, tuple) else (arg,)
            threads.append(threading.Thread(target=func, args=xarg))

    for t in threads:
        t.start()
    for t in threads:
        t.join()
