from pathlib import Path
from typing import Optional

from .common import get_files

from my.config import google as config

from .kython.kompress import kopen

def get_last_takeout(*, path: Optional[str]=None) -> Path:
    """
    Ok, sometimes google splits takeout into two zip archives
    I guess I could detect it (they've got 001/002 etc suffixes), but fornow that works fine..
    """
    for takeout in reversed(get_files(config.takeout_path, glob='*.zip')):
        if path is None:
            return takeout
        else:
            try:
                kopen(takeout, path)
                return takeout
            except:
                # TODO eh, a bit horrible, but works for now..
                # TODO move ot kompress? 'kexists'?
                continue
    raise RuntimeError(f'Not found: {path}')

# TODO might be a good idea to merge across multiple taekouts...
# perhaps even a special takeout module that deals with all of this automatically?
# e.g. accumulate, filter and maybe report useless takeouts?

