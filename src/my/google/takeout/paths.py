'''
Module for locating and accessing [[https://takeout.google.com][Google Takeout]] data
'''

from __future__ import annotations

from my.core import __NOT_HPI_MODULE__  # isort: skip

from abc import abstractmethod
from collections.abc import Iterable
from pathlib import Path

from more_itertools import last

from my.core import Paths, get_files


class config:
    """
    path/paths/glob for the takeout zips
    """

    @property
    @abstractmethod
    def takeout_path(self) -> Paths:
        raise NotImplementedError


# TODO rename 'google' to 'takeout'? not sure


def make_config() -> config:
    from my.config import google as user_config

    class combined_config(user_config, config): ...

    return combined_config()


def get_takeouts(*, path: str | None = None) -> Iterable[Path]:
    """
    Sometimes google splits takeout into multiple archives, so we need to detect the ones that contain the path we need
    """
    # TODO zip is not great..
    # allow a lambda expression? that way the user could restrict it
    cfg = make_config()
    for takeout in get_files(cfg.takeout_path, glob='*.zip'):
        if path is None or (takeout / path).exists():
            yield takeout


def get_last_takeout(*, path: str | None = None) -> Path | None:
    return last(get_takeouts(path=path), default=None)


# TODO might be a good idea to merge across multiple takeouts...
# perhaps even a special takeout module that deals with all of this automatically?
# e.g. accumulate, filter and maybe report useless takeouts?
