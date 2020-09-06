import sys
from pathlib import Path
from more_itertools import ilen

# TODO NOTE: this wouldn't work because of an early my.config.demo import
# from my.demo import items

def test_dynamic_config_1(tmp_path: Path) -> None:
    import my.config

    class user_config:
        username  = 'user'
        data_path = f'{tmp_path}/*.json'
        external  = f'{tmp_path}/external'
    my.config.demo = user_config # type: ignore[misc, assignment]

    from my.demo import items
    [item1, item2] = items()
    assert item1.username == 'user'


# exactly the same test, but using a different config, to test out the behavious w.r.t. import order
def test_dynamic_config_2(tmp_path: Path) -> None:
    # doesn't work without it!
    # because the config from test_dybamic_config_1 is cached in my.demo.demo
    del sys.modules['my.demo']

    import my.config

    class user_config:
        username  = 'user2'
        data_path = f'{tmp_path}/*.json'
        external  = f'{tmp_path}/external'
    my.config.demo = user_config # type: ignore[misc, assignment]

    from my.demo import items
    [item1, item2] = items()
    assert item1.username == 'user2'


import pytest # type: ignore

@pytest.mark.skip(reason="won't work at the moment because of inheritance")
def test_dynamic_config_simplenamespace(tmp_path: Path) -> None:
    # doesn't work without it!
    # because the config from test_dybamic_config_1 is cached in my.demo.demo
    del sys.modules['my.demo']

    import my.config
    from types import SimpleNamespace

    user_config = SimpleNamespace(
        username='user3',
        data_path=f'{tmp_path}/*.json',
    )
    my.config.demo = user_config # type: ignore[misc, assignment]

    from my.demo import config
    assert config.username == 'user3'


# make sure our config handling pattern does it as expected
def test_attribute_handling(tmp_path: Path) -> None:
    # doesn't work without it!
    # because the config from test_dybamic_config_1 is cached in my.demo.demo
    del sys.modules['my.demo']

    import pytz
    nytz = pytz.timezone('America/New_York')

    import my.config
    class user_config:
        # check that override is taken into the account
        timezone = nytz

        irrelevant = 'hello'

        username = 'UUU'
        data_path = f'{tmp_path}/*.json'
        external  = f'{tmp_path}/external'


    my.config.demo = user_config # type: ignore[misc, assignment]

    from my.demo import config

    assert config.username == 'UUU'

    # mypy doesn't know about it, but the attribute is there
    assert getattr(config, 'irrelevant') == 'hello'

    # check that overridden default attribute is actually getting overridden
    assert config.timezone == nytz



@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    (tmp_path / 'data.json').write_text('''
[
    {"key1": 1},
    {"key2": 2}
]
''')
    ext = tmp_path / 'external'
    ext.mkdir()
    (ext / '__init__.py').write_text('''
def identity(x):
    from .submodule import hello
    hello(x)
    return x

''')
    (ext / 'submodule.py').write_text('hello = lambda x: print("hello " + str(x))')
    yield
    ex = 'my.config.repos.external'
    if ex in sys.modules:
        del sys.modules[ex]
