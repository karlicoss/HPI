from my.core.util import __NOT_HPI_MODULE__


def _patch_browserexport_logs(level: int):
    # grab the computed level (respects LOGGING_LEVEL_ prefixes) and set it on the browserexport logger
    from browserexport.log import setup as setup_browserexport_logger

    setup_browserexport_logger(level)
