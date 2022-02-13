"""
Parses active browser history by backing it up with [[http://github.com/seanbreckenridge/sqlite_backup][sqlite_backup]]
"""

REQUIRES = ["browserexport", "sqlite_backup"]


from my.config import browser as user_config
from my.core import Paths, dataclass


@dataclass
class config(user_config.active_browser):
    # paths to sqlite database files which you use actively
    # to read from. For example:
    # from browserexport.browsers.all import Firefox
    # active_databases = Firefox.locate_database()
    export_path: Paths


from pathlib import Path
from typing import Sequence, Iterator

from my.core import get_files, Stats
from browserexport.merge import read_visits, Visit
from sqlite_backup import sqlite_backup

from .common import _patch_browserexport_logs

_patch_browserexport_logs()


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def history() -> Iterator[Visit]:
    for ad in inputs():
        conn = sqlite_backup(ad)
        assert conn is not None
        try:
            yield from read_visits(conn)
        finally:
            conn.close()


def stats() -> Stats:
    from my.core import stat

    return {**stat(history)}
