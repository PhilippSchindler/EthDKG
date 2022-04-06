from enum import IntEnum, auto

# helper class for large scale testing
# if the node is run using --enable-markers, the marker are written to stdout as soon as the specific states are reached

_state_updates_enabled = False
_last_update = 0


def enable_state_updates():
    global _state_updates_enabled
    _state_updates_enabled = True


class StateUpdate(IntEnum):

    NEW = auto()
    STARTED = auto()
    INITIALIZED = auto()

    WAITING_FOR_REGISTRATION_CONFIRMATION = auto()
    REGISTRATION_CONFIRMED = auto()
    REGISTRATION_PHASE_COMPLETED = auto()

    SETUP_COMPLETED = auto()

    WAITING_FOR_SHARING_CONFIRMATION = auto()
    SHARING_CONFIRMED = auto()
    SHARING_PHASE_COMPLETED = auto()
    SHARES_LOADED = auto()

    NO_DISPUTES_TO_SUBMIT = auto()
    WAITING_FOR_DISPUTE_CONFIRMATION = auto()  # either this or the next one must be triggers are triggers
    DISPUTE_CONFIRMED = auto()
    DISPUTES_COMPLETED = auto()
    DISPUTE_PHASE_COMPLETED = auto()
    DISPUTES_LOADED = auto()

    WAITING_FOR_KEY_SHARE_CONFIRMATION = auto()
    KEY_SHARE_CONFIRMED = auto()
    KEY_SHARING_PHASE_COMPLETED = auto()

    KEY_SHARES_LOADED = auto()
    NO_KEY_SHARE_RECOVERY = auto()
    WAITING_FOR_KEY_SHARE_RECOVERY_CONFIRMATION = auto()
    KEY_SHARE_RECOVERY_CONFIRMED = auto()
    KEY_SHARE_RECOVERIES_LOADED = auto()

    NO_SUBMISSION_OF_RECOVERED_KEY_SHARE = auto()
    WAITING_FOR_SUBMISSION_OF_RECOVERED_KEY_SHARE_CONFIRMATION = auto()
    SUBMISSION_OF_RECOVERED_KEY_SHARE_CONFIRMED = auto()
    SUBMISSION_OF_RECOVERED_KEY_SHARES_COMPLETED = auto()

    MASTER_KEY_DERIVED = auto()
    WAITING_FOR_MASTER_KEY_SUBMISSION_CONFIRMATION = auto()
    MASTER_KEY_SUBMISSION_CONFIRMED = auto()
    DKG_COMPLETED = auto()

    def __call__(self):
        if _state_updates_enabled:
            print()
            if hasattr(self, "logger"):
                self.logger.info(str(self))
            print(self, flush=True)
            input()

    @classmethod
    def set_logger(cls, logger):
        cls.logger = logger

