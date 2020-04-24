from pathlib import Path
from typing import Optional

from .common import get_files
from .kython.kompress import kopen, kexists

from my.config import google as config

def get_last_takeout(*, path: Optional[str]=None) -> Path:
    """
    Ok, sometimes google splits takeout into two zip archives
    I guess I could detect it (they've got 001/002 etc suffixes), but fornow that works fine..
    """
    # TODO FIXME zip is not great..
    # allow a lambda expression? that way the user could restrict it
    for takeout in reversed(get_files(config.takeout_path, glob='*.zip')):
        if path is None or kexists(takeout, path):
            return takeout
        else:
            continue
    raise RuntimeError(f'Not found: {path}')

# TODO might be a good idea to merge across multiple takeouts...
# perhaps even a special takeout module that deals with all of this automatically?
# e.g. accumulate, filter and maybe report useless takeouts?

