'''
Module for locating and accessing [[https://takeout.google.com][Google Takeout]] data
'''

from dataclasses import dataclass
from ...core.common import Paths, get_files
from ...core.util import __NOT_HPI_MODULE__

from my.config import google as user_config

from more_itertools import last

@dataclass
class google(user_config):
    takeout_path: Paths # path/paths/glob for the takeout zips
###

# TODO rename 'google' to 'takeout'? not sure

from ...core.cfg import make_config
config = make_config(google)

from pathlib import Path
from typing import Optional, Iterable

from ...core.kompress import kexists


def get_takeouts(*, path: Optional[str]=None) -> Iterable[Path]:
    """
    Sometimes google splits takeout into multiple archives, so we need to detect the ones that contain the path we need
    """
    # TODO FIXME zip is not great..
    # allow a lambda expression? that way the user could restrict it
    for takeout in get_files(config.takeout_path, glob='*.zip'):
        if path is None or kexists(takeout, path):
            yield takeout


def get_last_takeout(*, path: Optional[str]=None) -> Optional[Path]:
    return last(get_takeouts(path=path), default=None)


# TODO might be a good idea to merge across multiple takeouts...
# perhaps even a special takeout module that deals with all of this automatically?
# e.g. accumulate, filter and maybe report useless takeouts?

