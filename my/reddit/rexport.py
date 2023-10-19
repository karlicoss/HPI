"""
Reddit data: saved items/comments/upvotes/etc.
"""
REQUIRES = [
    'git+https://github.com/karlicoss/rexport',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from my.core import (
    get_files,
    make_logger,
    stat,
    Paths,
    Stats,
)
from my.core.cfg import make_config, Attrs
from my.core.common import mcachew

from my.config import reddit as uconfig

logger = make_logger(__name__)


@dataclass
class reddit(uconfig):
    '''
    Uses [[https://github.com/karlicoss/rexport][rexport]] output.
    '''

    # path[s]/glob to the exported JSON data
    export_path: Paths


# hmm, also nice thing about this is that migration is possible to test without the rest of the config?
def migration(attrs: Attrs) -> Attrs:
    # new structure, take top-level config and extract 'rexport' class
    # previously, 'rexport' key could be location of the rexport repo on disk
    if 'rexport' in attrs and not isinstance(attrs['rexport'], (str, Path)):
        ex: uconfig.rexport = attrs['rexport']
        attrs['export_path'] = ex.export_path
    else:
        from my.core.warnings import high

        high("""DEPRECATED! Please modify your reddit config to look like:

class reddit:
    class rexport:
        export_path: Paths = '/path/to/rexport/data'
            """)
        export_dir = 'export_dir'
        if export_dir in attrs: # legacy name
            attrs['export_path'] = attrs[export_dir]
            high(f'"{export_dir}" is deprecated! Please use "export_path" instead."')
    return attrs


config = make_config(reddit, migration=migration)

###
try:
    from rexport import dal
except ModuleNotFoundError as e:
    from my.core.compat import pre_pip_dal_handler

    dal = pre_pip_dal_handler('rexport', e, config, requires=REQUIRES)
# TODO ugh. this would import too early
# but on the other hand we do want to bring the objects into the scope for easier imports, etc. ugh!
# ok, fair enough I suppose. It makes sense to configure something before using it. can always figure it out later..
# maybe, the config could dynamically detect change and reimport itself? dunno.
###


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


# fmt: off
Uid         = dal.Sid  # str
Save        = dal.Save
Comment     = dal.Comment
Submission  = dal.Submission
Upvote      = dal.Upvote
# fmt: on


def _dal() -> dal.DAL:
    inp = list(inputs())
    return dal.DAL(inp)


cache = mcachew(depends_on=inputs)


@cache
def saved() -> Iterator[Save]:
    return _dal().saved()


@cache
def comments() -> Iterator[Comment]:
    return _dal().comments()


@cache
def submissions() -> Iterator[Submission]:
    return _dal().submissions()


@cache
def upvoted() -> Iterator[Upvote]:
    return _dal().upvoted()


def stats() -> Stats:
    return {
        # fmt: off
        **stat(saved      ),
        **stat(comments   ),
        **stat(submissions),
        **stat(upvoted    ),
        # fmt: on
    }
