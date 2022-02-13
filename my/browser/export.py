"""
Parses Browser history using [[http://github.com/seanbreckenridge/browserexport][browserexport]]
"""

REQUIRES = ["browserexport"]

from my.config import browser as user_config
from my.core import Paths, dataclass


@dataclass
class config(user_config.export):
    # path[s]/glob to your backed up browser history sqlite files
    export_path: Paths

    # paths to sqlite database files which you
    # use actively, which should be combined into your history
    # For example:
    # from browserexport.browsers.all import Firefox
    # active_databases = Firefox.locate_database()
    active_databases: Paths


import os
from pathlib import Path
from typing import Iterator, List

from sqlite_backup import sqlite_backup

from my.core import Stats, get_files, LazyLogger
from my.core.common import mcachew


# patch browserexport logs if HPI_LOGS is present
if "HPI_LOGS" in os.environ:
    from browserexport.log import setup as setup_browserexport_logger
    from my.core.logging import mklevel

    setup_browserexport_logger(mklevel(os.environ["HPI_LOGS"]))


logger = LazyLogger(__name__, level="warning")


from browserexport.merge import read_and_merge, merge_visits, Visit
from browserexport.parse import read_visits


# all of my backed up databases
def inputs() -> List[Path]:
    return list(get_files(config.export_path))


# return the visits from the active sqlite database,
# copying the active database into memory using
# https://github.com/seanbreckenridge/sqlite_backup
def _active_visits() -> List[Visit]:
    visits: List[Visit] = []
    active_dbs = get_files(config.active_databases or "")
    logger.debug(f"Reading from active databases: {active_dbs}")
    for ad in active_dbs:
        conn = sqlite_backup(ad)
        assert conn is not None
        try:
            # read visits, so can close the in-memory connection
            visits.extend(list(read_visits(conn)))
        finally:
            conn.close()
    logger.debug(f"Read {len(visits)} visits from active databases")
    return visits


Results = Iterator[Visit]


# don't put this behind cachew, since the active history database(s)
# are merged when this is called, whose contents may constantly change
def history() -> Results:
    yield from merge_visits([_history_from_backups(), _active_visits()])


@mcachew(depends_on=lambda: sorted(map(str, inputs())), logger=logger)
def _history_from_backups() -> Results:
    yield from read_and_merge(inputs())


def stats() -> Stats:
    from my.core import stat

    return {**stat(history)}
