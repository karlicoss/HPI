"""
Parses browser history using [[http://github.com/purarue/browserexport][browserexport]]
"""

REQUIRES = ["browserexport"]

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from browserexport.merge import Visit, read_and_merge

from my.core import (
    Paths,
    Stats,
    get_files,
    make_logger,
    stat,
)
from my.core.cachew import mcachew

from .common import _patch_browserexport_logs

import my.config  # isort: skip


@dataclass
class config(my.config.browser.export):
    # path[s]/glob to your backed up browser history sqlite files
    export_path: Paths


logger = make_logger(__name__)
_patch_browserexport_logs(logger.level)


# all of my backed up databases
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@mcachew(depends_on=inputs, logger=logger)
def history() -> Iterator[Visit]:
    yield from read_and_merge(inputs())


def stats() -> Stats:
    return {**stat(history)}
