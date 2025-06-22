"""
Reddit data: saved items/comments/upvotes/etc.
"""
from __future__ import annotations

REQUIRES = [
    'git+https://github.com/karlicoss/rexport',
]

import inspect
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from my.core import (
    Paths,
    Stats,
    get_files,
    make_logger,
    stat,
    warnings,
)
from my.core.cachew import mcachew
from my.core.cfg import Attrs, make_config

from my.config import reddit as uconfig  # isort: skip

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
        warnings.high(
            """DEPRECATED! Please modify your reddit config to look like:

class reddit:
    class rexport:
        export_path: Paths = '/path/to/rexport/data'
            """
        )
        export_dir = 'export_dir'
        if export_dir in attrs:  # legacy name
            attrs['export_path'] = attrs[export_dir]
            warnings.high(f'"{export_dir}" is deprecated! Please use "export_path" instead."')
    return attrs


config = make_config(reddit, migration=migration)

###
try:
    from rexport import dal
except ModuleNotFoundError as e:
    from my.core.hpi_compat import pre_pip_dal_handler

    dal = pre_pip_dal_handler('rexport', e, config, requires=REQUIRES)
# TODO ugh. this would import too early
# but on the other hand we do want to bring the objects into the scope for easier imports, etc. ugh!
# ok, fair enough I suppose. It makes sense to configure something before using it. can always figure it out later..
# maybe, the config could dynamically detect change and reimport itself? dunno.
###


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


# TODO hmm so maybe these import here are not so great
# the issue is when the dal is updated (e.g. more types added)
# then user's state can be inconsistent if they update HPI, but don't update the dal
# maybe best to keep things begind the DAL after all

# fmt: off
Uid         = dal.Sid  # str
Save        = dal.Save
Comment     = dal.Comment
Submission  = dal.Submission
Upvote      = dal.Upvote
# fmt: on


def _dal() -> dal.DAL:
    sources = list(inputs())

    ## backwards compatibility (old rexport DAL didn't have cpu_pool argument)
    cpu_pool_arg = 'cpu_pool'
    pass_cpu_pool = cpu_pool_arg in inspect.signature(dal.DAL).parameters
    if pass_cpu_pool:
        from my.core._cpu_pool import get_cpu_pool

        kwargs = {cpu_pool_arg: get_cpu_pool()}
    else:
        kwargs = {}
    ##
    return dal.DAL(sources, **kwargs)


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


# uhh.. so with from __future__ import annotations, in principle we don't need updated export
# (with new entity types for function definitions below)
# however, cachew (as of 0.14.20231004) will crash during to get_type_hints call with these
# so we need to make cachew decorating defensive here
# will need to keep this for some time for backwards compatibility till cachew fix catches up
if not TYPE_CHECKING:
    # in runtime need to be defensive
    try:
        # here we just check that types are available, we don't actually want to import them
        # fmt: off
        dal.Subreddit  # noqa: B018
        dal.Profile  # noqa: B018
        dal.Multireddit  # noqa: B018
        # fmt: on
    except AttributeError as ae:
        warnings.high(f'{ae} : please update "rexport" installation')
        _cache = lambda f: f
        _USING_NEW_REXPORT = False
    else:
        _cache = cache
        _USING_NEW_REXPORT = True
else:
    _cache = cache


@_cache
def subreddits() -> Iterator[dal.Subreddit]:
    return _dal().subreddits()


@_cache
def multireddits() -> Iterator[dal.Multireddit]:
    return _dal().multireddits()


@_cache
def profile() -> dal.Profile:
    return _dal().profile()


def stats() -> Stats:
    # fmt: off
    return {
        **stat(saved      ),
        **stat(comments   ),
        **stat(submissions),
        **stat(upvoted    ),
    }
    # fmt: on
