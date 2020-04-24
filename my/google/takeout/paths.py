from pathlib import Path
from typing import Optional, Iterable

from ...common import get_files
from ...kython.kompress import kopen, kexists

from my.config import google as config

def get_takeouts(*, path: Optional[str]=None) -> Iterable[Path]:
    """
    Sometimes google splits takeout into multiple archives, so we need to detect the ones that contain the path we need
    """
    # TODO FIXME zip is not great..
    # allow a lambda expression? that way the user could restrict it
    for takeout in get_files(config.takeout_path, glob='*.zip'):
        if path is None or kexists(takeout, path):
            yield takeout


def get_last_takeout(*, path: Optional[str]=None) -> Path:
    # TODO more_itertools?
    matching = list(get_takeouts(path=path))
    return matching[-1]


# TODO might be a good idea to merge across multiple takeouts...
# perhaps even a special takeout module that deals with all of this automatically?
# e.g. accumulate, filter and maybe report useless takeouts?

