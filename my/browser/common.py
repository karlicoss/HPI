import os
from my.core.util import __NOT_HPI_MODULE__


def _patch_browserexport_logs():
    # patch browserexport logs if HPI_LOGS is present
    if "HPI_LOGS" in os.environ:
        from browserexport.log import setup as setup_browserexport_logger
        from my.core.logging import mklevel

        setup_browserexport_logger(mklevel(os.environ["HPI_LOGS"]))
