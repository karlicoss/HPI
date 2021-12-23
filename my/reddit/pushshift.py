"""
Gives you access to older comments possibly not accessible with rexport
using pushshift
See https://github.com/seanbreckenridge/pushshift_comment_export
"""

REQUIRES = [
    "git+https://github.com/seanbreckenridge/pushshift_comment_export",
]

from my.core.common import Paths, Stats
from dataclasses import dataclass
from my.core.cfg import make_config

# note: keeping pushshift import before config import, so it's handled gracefully by import_source
from pushshift_comment_export.dal import read_file, PComment

from my.config import reddit as uconfig

@dataclass
class pushshift_config(uconfig.pushshift):
    '''
    Uses [[https://github.com/seanbreckenridge/pushshift_comment_export][pushshift]] to get access to old comments
    '''

    # path[s]/glob to the exported JSON data
    export_path: Paths

config = make_config(pushshift_config)

from my.core import get_files
from typing import Sequence, Iterator
from pathlib import Path



def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def comments() -> Iterator[PComment]:
    for f in inputs():
        yield from read_file(f)

def stats() -> Stats:
    from my.core import stat
    return {
        **stat(comments)
    }

