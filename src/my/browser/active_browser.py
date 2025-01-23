"""
Parses active browser history by backing it up with [[http://github.com/purarue/sqlite_backup][sqlite_backup]]
"""

REQUIRES = ["browserexport", "sqlite_backup"]

from dataclasses import dataclass

from my.config import browser as user_config
from my.core import Paths


@dataclass
class config(user_config.active_browser):
    # paths to sqlite database files which you use actively
    # to read from. For example:
    # from browserexport.browsers.all import Firefox
    # export_path = Firefox.locate_database()
    export_path: Paths


from collections.abc import Iterator, Sequence
from pathlib import Path

from browserexport.merge import Visit, read_visits
from sqlite_backup import sqlite_backup

from my.core import Stats, get_files, make_logger

logger = make_logger(__name__)

from .common import _patch_browserexport_logs

_patch_browserexport_logs(logger.level)


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
