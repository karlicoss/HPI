"""
Module for Facebook Messenger messages
"""

from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import Iterator, Union

import mycfg.repos.fbmessengerexport.dal as messenger
from mycfg import paths


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


def get_model() -> messenger.DAL:
    return messenger.DAL(paths.fbmessenger.export_db)


# TODO FIXME Result type?
def iter_all_messages() -> Iterator[messenger.Message]:
    model = get_model()
    for t in model.iter_threads():
        yield from t.iter_messages()


def dump_chat_history(where: Union[Path, str]) -> None:
    p = Path(where)
    assert not p.exists() or p.is_dir()

    model = get_model()

    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        _dump_helper(model, td)

        if p.exists():
            rmtree(p)
        td.rename(p)
        td.mkdir() # ugh, hacky way of preventing complaints from context manager
