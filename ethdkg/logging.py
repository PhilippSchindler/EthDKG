import logging
import os.path
import subprocess
import types

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
LOG_FORMAT_NO_TIMESTAMPS = "%(levelname)-8s %(message)s"

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))

RESET = "\033[0;0m"
COLORS = {
    logging.DEBUG: RESET,
    logging.INFO: RESET,
    logging.WARNING: "\033[1;33m",
    logging.ERROR: "\033[1;31m",
    logging.CRITICAL: "\033[1;31m",
    logging.INFO: "\033[0;0m",
}


class CustomCLIFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style="%", line_length=None):
        super().__init__(fmt, datefmt, style)
        self.line_length = line_length

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)

        # if record.levelno > logging.INFO:
        msg = f"{COLORS[record.levelno]}{record.levelname: <10}{msg}{RESET}"

        if len(msg) > self.line_length:
            return msg[: self.line_length - 3] + "..."
        return msg


def create_logger(filename, cli_linewidth="auto", log_timestamps=False):
    if cli_linewidth == "auto":
        cli_linewidth = int(subprocess.check_output(["tput", "cols"]).decode())

    filepath = os.path.join(LOG_DIR, filename)

    cli_handler = logging.StreamHandler()
    cli_handler.setLevel(logging.DEBUG)
    cli_formatter = CustomCLIFormatter(line_length=cli_linewidth)
    cli_handler.setFormatter(cli_formatter)

    file_handler = logging.FileHandler(filepath, "w")
    file_handler.setLevel(logging.DEBUG)
    if log_timestamps:
        file_formatter = logging.Formatter(LOG_FORMAT, "%Y-%m-%d %H:%M:%S")
    else:
        file_formatter = logging.Formatter(LOG_FORMAT_NO_TIMESTAMPS)

    file_handler.setFormatter(file_formatter)

    newline_formatter = logging.Formatter("")

    def newline(self, how_many_lines=1):
        cli_handler.setFormatter(newline_formatter)
        file_handler.setFormatter(newline_formatter)
        for i in range(how_many_lines):
            self.info("")
        cli_handler.setFormatter(cli_formatter)
        file_handler.setFormatter(file_formatter)

    logger = logging.getLogger("ethdkg-logger")
    logger.addHandler(cli_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    logger.newline = types.MethodType(newline, logger)

    return logger


class _NullLogger:
    def info(self, *args, **kwargs):
        pass

    debug = info
    warn = info
    warning = info
    error = info
    critical = info
    newline = info


NullLogger = _NullLogger()

