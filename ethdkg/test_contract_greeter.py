from . import utils


def test_compilation():
    utils.compile_contract("Greeter")


def test_deployment():
    utils.compile_contract("Greeter")
    contract = utils.deploy_contract("Greeter")
    assert contract.caller.greet() == "Hello World!"
    assert contract.caller.greeting() == "Hello World!"


def test_getter():
    utils.compile_contract("Greeter")
    contract = utils.deploy_contract("Greeter")
    tx_hash = contract.functions.setGreeting("Hello pytest!").transact(
        {"from": utils.get_account_address()}
    )
    utils.mine_block()
    tx_receipt = utils.wait_for_tx_receipt(tx_hash)
    assert contract.caller.greet() == "Hello pytest!"
    assert contract.caller.greeting() == "Hello pytest!"

