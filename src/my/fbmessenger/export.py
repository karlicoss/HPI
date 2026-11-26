"""
Facebook Messenger messages

Uses the output of [[https://github.com/karlicoss/fbmessengerexport][fbmessengerexport]]
"""

REQUIRES = [
    'fbmessengerexport @ git+https://github.com/karlicoss/fbmessengerexport',
]

from abc import abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import fbmessengerexport.dal as messenger

from my.config import fbmessenger as user_config
from my.core import Res, Stats, stat
from my.core.warnings import high

###
# support old style config
_new_section = getattr(user_config, 'fbmessengerexport', None)
_old_attr    = getattr(user_config, 'export_db', None)  # fmt: skip

if _new_section is None and _old_attr is not None:
    high("""DEPRECATED! Modify your fbmessenger config to look like:

class fbmessenger:
    class fbmessengerexport:
        export_db: Path | str = '/path/to/fbmessengerexport/database'
            """)

    class fbmessengerexport:
        export_db = _old_attr

    setattr(user_config, 'fbmessengerexport', fbmessengerexport)
###


class Config(Protocol):
    @property
    @abstractmethod
    def export_db(self) -> Path | str:
        raise NotImplementedError


class config(user_config.fbmessengerexport, Config):
    pass


def _dal() -> messenger.DAL:
    return messenger.DAL(config.export_db)


def messages() -> Iterator[Res[messenger.Message]]:
    with _dal() as model:
        for t in model.iter_threads():
            yield from t.iter_messages()


def stats() -> Stats:
    return stat(messages)
