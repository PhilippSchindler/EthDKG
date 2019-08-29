from . import utils


def test_addr_cast():
    # ethereum address are uses as integer indices in the secret sharing protocol
    # check to ensure that python and solidity actually do the same thing

    utils.compile_contract("Testing")
    contract = utils.deploy_contract("Testing")

    addr = utils.get_account_address()
    addr_as_uint256 = int(addr, 16)
    tx_receipt = contract.test_addr_cast(addr_as_uint256).call_sync()

    assert tx_receipt.status == utils.STATUS_OK


def test_points():
    # ethereum address are uses as integer indices in the secret sharing protocol
    # check to ensure that python and solidity actually do the same thing

    utils.compile_contract("Testing")
    contract = utils.deploy_contract("Testing")

    tx_receipt = contract.do_something_with_points([(1, 2), (3, 4)]).call_sync()
    assert tx_receipt.status == utils.STATUS_OK

    tx_receipt = contract.do_something_with_uint256_tuples([(1, 2), (3, 4)]).call_sync()
    assert tx_receipt.status == utils.STATUS_OK


def test_list_assignment():
    utils.compile_contract("Testing")
    contract = utils.deploy_contract("Testing")

    tx_receipt = contract.set_some_point([1, 2]).call_sync()
    assert tx_receipt.status == utils.STATUS_OK

    assert contract.caller.some_point(0) == 1
    assert contract.caller.some_point(1) == 2


def test_event_filters():
    utils.compile_contract("Testing")
    contract = utils.deploy_contract("Testing")

    contract.trigger_something(1991).call_sync()

    f = contract.events.SomethingHappend.createFilter(fromBlock=0)
    assert len(f.get_all_entries()) == 1

    contract.trigger_something(1991).call_sync()
    assert len(f.get_new_entries()) == 1
    assert len(f.get_all_entries()) == 2

