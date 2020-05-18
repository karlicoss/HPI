'''
Just a demo module for testing and documentation purposes
'''

from .core import Paths, PathIsh

from typing import Optional
from datetime import tzinfo
import pytz

from my.config import demo as user_config
from dataclasses import dataclass


@dataclass
class demo(user_config):
    data_path: Paths
    username: str
    timezone: tzinfo = pytz.utc

    external: Optional[PathIsh] = None

    @property
    def external_module(self):
        rpath = self.external
        if rpath is not None:
            from .core.common import import_dir
            return import_dir(rpath)

        import my.config.repos.external as m # type: ignore
        return m


from .core import make_config
config = make_config(demo)

# TODO not sure about type checking?
external = config.external_module


from pathlib import Path
from typing import Sequence, Iterable
from datetime import datetime
from .core import Json, get_files

@dataclass
class Item:
    '''
    Some completely arbirary artificial stuff, just for testing
    '''
    username: str
    raw: Json
    dt: datetime


def inputs() -> Sequence[Path]:
    return get_files(config.data_path)


import json
def items() -> Iterable[Item]:
    for f in inputs():
        dt = datetime.fromtimestamp(f.stat().st_mtime, tz=config.timezone)
        j = json.loads(f.read_text())
        for raw in j:
            yield Item(
                username=config.username,
                raw=external.identity(raw),
                dt=dt,
            )
