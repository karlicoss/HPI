from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import Union

import my_configuration.repos.fbmessengerexport.model as messenger
from my_configuration import paths


def _dump_helper(model: messenger.Model, tdir: Path) -> None:
    for t in model.iter_threads():
        name = t.name.replace('/', '_') # meh..
        path = tdir / (name + '.txt')
        with path.open('w') as fo:
            for m in t.iter_messages(order_by='-timestamp'):
                # TODO would be nice to have usernames perhaps..
                dts = m.dt.strftime('%Y-%m-%d %a %H:%M')
                msg = f"{dts}: {m.text}"
                print(msg, file=fo)


def dump_chat_history(path: Union[Path, str]) -> None:
    p = Path(path)
    assert not p.exists() or p.is_dir()

    m = messenger.Model(paths.fbmessenger.export_db)

    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        _dump_helper(m, td)

        if p.exists():
            rmtree(p)
        td.rename(p)
        td.mkdir() # ugh, hacky way of preventing complaints from context manager
