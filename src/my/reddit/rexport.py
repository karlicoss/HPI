"""
Reddit data: saved items/comments/upvotes/etc.
"""

from __future__ import annotations

REQUIRES = [
    'rexport @ git+https://github.com/karlicoss/rexport',
]

import inspect
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from pathlib import Path

from rexport import dal

from my.core import (
    Paths,
    Res,
    Stats,
    get_files,
    make_logger,
    stat,
)
from my.core.cachew import mcachew

logger = make_logger(__name__)


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to [[https://github.com/karlicoss/rexport][rexport]] JSON exports."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import reddit as user_config

    class combined_config(user_config.rexport, Config):
        pass

    return combined_config()


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


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
def saved() -> Iterator[Res[Save]]:
    return _dal().saved()


@cache
def comments() -> Iterator[Res[Comment]]:
    return _dal().comments()


@cache
def submissions() -> Iterator[Res[Submission]]:
    return _dal().submissions()


@cache
def upvoted() -> Iterator[Res[Upvote]]:
    return _dal().upvoted()


@cache
def subreddits() -> Iterator[Res[dal.Subreddit]]:
    return _dal().subreddits()


@cache
def multireddits() -> Iterator[Res[dal.Multireddit]]:
    return _dal().multireddits()


@cache
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
