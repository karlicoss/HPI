"""
Facebook Messenger messages

Uses the output of [[https://github.com/karlicoss/fbmessengerexport][fbmessengerexport]]
"""
REQUIRES = [
    'git+https://github.com/karlicoss/fbmessengerexport',
]

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass

import fbmessengerexport.dal as messenger

from my.config import fbmessenger as user_config
from my.core import PathIsh, Res, Stats, stat
from my.core.warnings import high

###
# support old style config
_new_section = getattr(user_config, 'fbmessengerexport', None)
_old_attr    = getattr(user_config, 'export_db', None)

if _new_section is None and _old_attr is not None:
    high("""DEPRECATED! Please modify your fbmessenger config to look like:

class fbmessenger:
    class fbmessengerexport:
        export_db: PathIsh = '/path/to/fbmessengerexport/database'
            """)
    class fbmessengerexport:
        export_db = _old_attr
    setattr(user_config, 'fbmessengerexport', fbmessengerexport)
###


@dataclass
class config(user_config.fbmessengerexport):
    export_db: PathIsh


@contextmanager
def _dal() -> Iterator[messenger.DAL]:
    model = messenger.DAL(config.export_db)
    with ExitStack() as stack:
        if hasattr(model, '__dal__'):  # defensive to support legacy fbmessengerexport
            stack.enter_context(model)
        yield model


def messages() -> Iterator[Res[messenger.Message]]:
    with _dal() as model:
        for t in model.iter_threads():
            yield from t.iter_messages()


def stats() -> Stats:
    return stat(messages)
