import utils


w3 = utils.connect()
contract = utils.deploy_contract('Greeter')


def test_initial():
    assert contract.greet() == 'Hello'


def test_update():
    contract.setGreeting('Nihao', transact={'from': w3.eth.accounts[-1]})
    assert contract.greet() == 'Nihao'


def test_array_parameter():
    contract.doSomethingWithArray([1, 2, 3], transact={'from': w3.eth.accounts[-1]})
    assert contract.getNumbers() == [1, 2, 3]


def test_revert():
    # for now there seams to be no easy way to access the tx hash of the reverted transaction for web3py
    try:
        tx_hash = contract.test_revert(wait=False, transact={'from': w3.eth.accounts[-1]})
        print(tx_hash)
    except ValueError:
        pass
