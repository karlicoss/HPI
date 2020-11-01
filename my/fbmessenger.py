"""
Facebook Messenger messages

Uses the output of [[https://github.com/karlicoss/fbmessengerexport][fbmessengerexport]]
"""
REQUIRES = [
    'git+https://github.com/karlicoss/fbmessengerexport',
]

from pathlib import Path
from typing import Iterator

from .core import PathIsh

import fbmessengerexport.dal as messenger

from my.config import fbmessenger as config


def _dal() -> messenger.DAL:
    return messenger.DAL(config.export_db)


# TODO Result type?
def messages() -> Iterator[messenger.Message]:
    model = _dal()
    for t in model.iter_threads():
        yield from t.iter_messages()


from .core import stat, Stats
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
