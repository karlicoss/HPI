"""
Parses browser history using [[http://github.com/seanbreckenridge/browserexport][browserexport]]
"""

REQUIRES = ["browserexport"]

from my.config import browser as user_config
from my.core import Paths, dataclass


@dataclass
class config(user_config.export):
    # path[s]/glob to your backed up browser history sqlite files
    export_path: Paths


from pathlib import Path
from typing import Iterator, Sequence, List

from my.core import Stats, get_files, LazyLogger
from my.core.common import mcachew

from browserexport.merge import read_and_merge, Visit

from .common import _patch_browserexport_logs


logger = LazyLogger(__name__, level="warning")

_patch_browserexport_logs()


# all of my backed up databases
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def _cachew_depends_on() -> List[str]:
    return [str(f) for f in inputs()]


@mcachew(depends_on=_cachew_depends_on, logger=logger)
def history() -> Iterator[Visit]:
    yield from read_and_merge(inputs())


def stats() -> Stats:
    from my.core import stat

    return {**stat(history)}
