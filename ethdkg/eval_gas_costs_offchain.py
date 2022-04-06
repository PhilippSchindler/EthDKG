import time
from . import utils

utils.compile_contract("OffchainDKG")
contract = utils.deploy_contract("OffchainDKG", should_add_simplified_call_interfaces=False)

time.sleep(1.0)

