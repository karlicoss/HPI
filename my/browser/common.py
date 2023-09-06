from my.core import make_logger
from my.core.util import __NOT_HPI_MODULE__


def _patch_browserexport_logs(module_name: str):
    # get the logger for the module this is being called from
    module_logger = make_logger(module_name)

    # grab the computed level (respects LOGGING_LEVEL_ prefixes) and set it on the browserexport logger
    from browserexport.log import setup as setup_browserexport_logger

    setup_browserexport_logger(module_logger.level)
