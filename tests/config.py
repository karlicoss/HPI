from pathlib import Path


def setup_notes_path(notes: Path) -> None:
    # TODO reuse doc from my.cfg?
    from my.cfg import config

    class user_config:
        paths = [notes]
    config.orgmode = user_config # type: ignore[misc,assignment]
    # TODO  ugh. this belongs to tz provider or global config or someting
    import pytz
    class user_config_2:
        default_timezone = pytz.timezone('Europe/London')
    config.weight  = user_config_2 # type: ignore[attr-defined,assignment]


def test_dynamic_configuration(notes: Path) -> None:
    setup_notes_path(notes)

    from my.body.weight import from_orgmode
    weights = [0.0 if isinstance(x, Exception) else x.value for x in from_orgmode()]

    assert weights == [
        0.0,
        62.0,
        0.0,
        61.0,
        62.0,
        0.0,
    ]

import pytest # type: ignore


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


from dataclasses import dataclass


def test_user_config() -> None:
    from my.core.common import classproperty
    class user_config:
        param1 = 'abacaba'
        # TOOD fuck. properties don't work here???
        @classproperty
        def param2(cls) -> int:
            return 456

        extra = 'extra!'

    @dataclass
    class test_config(user_config):
        param1: str
        param2: int # type: ignore[assignment] # TODO need to figure out how to trick mypy for @classproperty
        param3: str = 'default'

    assert test_config.param1 == 'abacaba'
    assert test_config.param2 == 456
    assert test_config.param3 == 'default'
    assert test_config.extra  == 'extra!'

    from my.core.cfg import make_config
    c = make_config(test_config)
    assert c.param1 == 'abacaba'
    assert c.param2 == 456
    assert c.param3 == 'default'
    assert c.extra  == 'extra!'


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
    this should be ignored, got no timestamp
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
