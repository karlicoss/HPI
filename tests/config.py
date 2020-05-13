from pathlib import Path


# TODO switch these from using SimpleNamespace

def setup_notes_path(notes: Path) -> None:
    # TODO reuse doc from my.cfg?
    from my.cfg import config

    from types import SimpleNamespace
    config.orgmode = SimpleNamespace( # type: ignore[misc,assignment]
        roots=[notes],
    )
    # TODO FIXME ugh. this belongs to tz provider or global config or someting
    import pytz
    config.weight  = SimpleNamespace( # type: ignore[misc,assignment]
        default_timezone = pytz.timezone('Europe/London')
    )


def test_dynamic_configuration(notes: Path) -> None:
    setup_notes_path(notes)

    from my.body.weight import dataframe
    weight_df = dataframe()

    assert list(weight_df['weight'].fillna(0.0)) == [
        0.0,
        62.0,
        0.0,
        61.0,
        62.0,
        0.0,
    ]

import pytest # type: ignore


def test_set_repo(tmp_path: Path) -> None:
    from my.cfg import config
    from types import SimpleNamespace
    config.hypothesis = SimpleNamespace( # type: ignore[misc,assignment]
        export_path='whatever',
    )

    # precondition:
    # should fail because can't find hypexport
    with pytest.raises(ModuleNotFoundError):
        import my.hypothesis

    fake_hypexport = tmp_path / 'hypexport'
    fake_hypexport.mkdir()
    (fake_hypexport / 'dal.py').write_text('''
Highlight = None
Page = None
DAL = None
    ''')

    from my.cfg import set_repo
    set_repo('hypexport', fake_hypexport)

    # should succeed now!
    import my.hypothesis


def test_environment_variable(tmp_path: Path) -> None:
    cfg_dir  = tmp_path / 'my'
    cfg_file = cfg_dir / 'config.py'
    cfg_dir.mkdir()
    cfg_file.write_text('''
class feedly:
    pass
''')

    import os
    os.environ['MY_CONFIG'] = str(tmp_path)

    # should not raise at least
    import my.rss.feedly


@pytest.fixture
def notes(tmp_path: Path):
    ndir = tmp_path / 'notes'
    ndir.mkdir()
    logs = ndir / 'logs.org'
    logs.write_text('''
#+TITLE: Stuff I'm logging

* Weight (org-capture) :weight:
** [2020-05-01 Fri 09:00] 62
** 63
    this should be ignored, got no timestmap
** [2020-05-03 Sun 08:00] 61
** [2020-05-04 Mon 10:00] 62
    ''')
    misc = ndir / 'misc.org'
    misc.write_text('''
Some misc stuff

* unrelated note :weight:whatever:
    ''')
    try:
        yield ndir
    finally:
        pass


@pytest.fixture(autouse=True)
def reset_config():
    # otherwise tests impact each other because of the cached my. modules...
    # hacky, but does the trick?
    import sys
    import re
    to_unload = [m for m in sys.modules if re.match(r'my[.]?', m)]
    for m in to_unload:
        del sys.modules[m]
    yield
