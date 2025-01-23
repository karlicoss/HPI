"""
Gives you access to older comments possibly not accessible with rexport
using pushshift
See https://github.com/purarue/pushshift_comment_export
"""

REQUIRES = [
    "git+https://github.com/purarue/pushshift_comment_export",
]

from dataclasses import dataclass

# note: keeping pushshift import before config import, so it's handled gracefully by import_source
from pushshift_comment_export.dal import PComment, read_file

from my.config import reddit as uconfig
from my.core import Paths, Stats, stat
from my.core.cfg import make_config


@dataclass
class pushshift_config(uconfig.pushshift):
    '''
    Uses [[https://github.com/purarue/pushshift_comment_export][pushshift]] to get access to old comments
    '''

    # path[s]/glob to the exported JSON data
    export_path: Paths

config = make_config(pushshift_config)

from collections.abc import Iterator, Sequence
from pathlib import Path

from my.core import get_files


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def comments() -> Iterator[PComment]:
    for f in inputs():
        yield from read_file(f)

def stats() -> Stats:
    return {
        **stat(comments)
    }

