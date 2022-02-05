"""
Facebook Messenger messages

Uses the output of [[https://github.com/karlicoss/fbmessengerexport][fbmessengerexport]]
"""
REQUIRES = [
    'git+https://github.com/karlicoss/fbmessengerexport',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from my.config import fbmessenger as user_config

import fbmessengerexport.dal as messenger


###
# support old style config
_new_section = getattr(user_config, 'fbmessengerexport', None)
_old_attr    = getattr(user_config, 'export_db', None)

if _new_section is None and _old_attr is not None:
    from my.core.warnings import high
    high("""DEPRECATED! Please modify your fbmessenger config to look like:

class fbmessenger:
    class fbmessengerexport:
        export_db: PathIsh = '/path/to/fbmessengerexport/database'
            """)
    class fbmessengerexport:
        export_db = _old_attr
    setattr(user_config, 'fbmessengerexport', fbmessengerexport)
###


from ..core import PathIsh
@dataclass
class config(user_config.fbmessengerexport):
    export_db: PathIsh


def _dal() -> messenger.DAL:
    return messenger.DAL(config.export_db)


from ..core import Res
def messages() -> Iterator[Res[messenger.Message]]:
    model = _dal()
    for t in model.iter_threads():
        yield from t.iter_messages()


from ..core import stat, Stats
def stats() -> Stats:
    return stat(messages)


### vvv not sure if really belongs here...

def _dump_helper(model: messenger.DAL, tdir: Path) -> None:
    for t in model.iter_threads():
        name = t.name.replace('/', '_') # meh..
        path = tdir / (name + '.txt')
        with path.open('w') as fo:
            for m in t.iter_messages(order_by='-timestamp'):
                # TODO would be nice to have usernames perhaps..
                dts = m.dt.strftime('%Y-%m-%d %a %H:%M')
                msg = f"{dts}: {m.text}"
                print(msg, file=fo)


def dump_chat_history(where: PathIsh) -> None:
    p = Path(where)
    assert not p.exists() or p.is_dir()

    model = _dal()

    from shutil import rmtree
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        _dump_helper(model, td)

        if p.exists():
            rmtree(p)
        td.rename(p)
        td.mkdir() # ugh, hacky way of preventing complaints from context manager
