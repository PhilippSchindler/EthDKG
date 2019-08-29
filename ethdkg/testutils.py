from . import utils


def mine_until_registrations_confirmed(contract):
    T = contract.caller.T_REGISTRATION_END() + contract.caller.DELTA_CONFIRM()
    utils.mine_blocks_until(lambda: utils.block_number() > T)


def mine_until_share_distribution_confirmed(contract):
    T = contract.caller.T_SHARE_DISTRIBUTION_END() + contract.caller.DELTA_CONFIRM()
    utils.mine_blocks_until(lambda: utils.block_number() > T)


def mine_until_disputes_confirmed(contract):
    T = contract.caller.T_DISPUTE_END() + contract.caller.DELTA_CONFIRM()
    utils.mine_blocks_until(lambda: utils.block_number() > T)


def mine_until_key_share_submission_confirmed(contract):
    T = (
        contract.caller.T_DISPUTE_END()
        + contract.caller.DELTA_INCLUDE()
        + contract.caller.DELTA_CONFIRM() * 2
    )
    utils.mine_blocks_until(lambda: utils.block_number() > T)
