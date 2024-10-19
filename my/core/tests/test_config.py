"""
Various tests that are checking behaviour of user config wrt to various things
"""

import os
import sys
from pathlib import Path

import pytest
import pytz

import my.config
from my.core import notnone
from my.demo import items, make_config

from .common import tmp_environ_set

# TODO would be nice to randomize test order here to catch various config issues


# run the same test multiple times to make sure there are not issues with import order etc
@pytest.mark.parametrize('run_id', ['1', '2'])
def test_override_config(tmp_path: Path, run_id: str) -> None:
    class user_config:
        username = f'user_{run_id}'
        data_path = f'{tmp_path}/*.json'

    my.config.demo = user_config  # type: ignore[misc, assignment]

    [item1, item2] = items()
    assert item1.username == f'user_{run_id}'
    assert item2.username == f'user_{run_id}'


@pytest.mark.skip(reason="won't work at the moment because of inheritance")
def test_dynamic_config_simplenamespace(tmp_path: Path) -> None:
    from types import SimpleNamespace

    user_config = SimpleNamespace(
        username='user3',
        data_path=f'{tmp_path}/*.json',
    )
    my.config.demo = user_config  # type: ignore[misc, assignment]

    cfg = make_config()

    assert cfg.username == 'user3'


def test_mixin_attribute_handling(tmp_path: Path) -> None:
    """
    Tests that arbitrary mixin attributes work with our config handling pattern
    """

    nytz = pytz.timezone('America/New_York')

    class user_config:
        # check that override is taken into the account
        timezone = nytz

        irrelevant = 'hello'

        username = 'UUU'
        data_path = f'{tmp_path}/*.json'

    my.config.demo = user_config  # type: ignore[misc, assignment]

    cfg = make_config()

    assert cfg.username == 'UUU'

    # mypy doesn't know about it, but the attribute is there
    assert getattr(cfg, 'irrelevant') == 'hello'

    # check that overridden default attribute is actually getting overridden
    assert cfg.timezone == nytz

    [item1, item2] = items()
    assert item1.username == 'UUU'
    assert notnone(item1.dt.tzinfo).zone == nytz.zone  # type: ignore[attr-defined]
    assert item2.username == 'UUU'
    assert notnone(item2.dt.tzinfo).zone == nytz.zone  # type: ignore[attr-defined]


# use multiple identical tests to make sure there are no issues with cached imports etc
@pytest.mark.parametrize('run_id', ['1', '2'])
def test_dynamic_module_import(tmp_path: Path, run_id: str) -> None:
    """
    Test for dynamic hackery in config properties
     e.g. importing some external modules
    """

    ext = tmp_path / 'external'
    ext.mkdir()
    (ext / '__init__.py').write_text(
        '''
def transform(x):
    from .submodule import do_transform
    return do_transform(x)

'''
    )
    (ext / 'submodule.py').write_text(
        f'''
def do_transform(x):
    return {{"total_{run_id}": sum(x.values())}}
'''
    )

    class user_config:
        username = 'someuser'
        data_path = f'{tmp_path}/*.json'
        external = f'{ext}'

    my.config.demo = user_config  # type: ignore[misc, assignment]

    [item1, item2] = items()
    assert item1.raw == {f'total_{run_id}': 1 + 123}, item1
    assert item2.raw == {f'total_{run_id}': 2 + 456}, item2

    # need to reset these modules, otherwise they get cached
    # kind of relevant to my.core.cfg.tmp_config
    sys.modules.pop('external', None)
    sys.modules.pop('external.submodule', None)


@pytest.mark.parametrize('run_id', ['1', '2'])
def test_my_config_env_variable(tmp_path: Path, run_id: str) -> None:
    """
    Tests handling of MY_CONFIG variable
    """

    # ugh. so by this point, my.config is already loaded (default stub), so we need to unload it
    sys.modules.pop('my.config', None)
    # but my.config itself relies on my.core.init hook, so unless it's reloaded too it wouldn't help
    sys.modules.pop('my.core', None)
    sys.modules.pop('my.core.init', None)
    # it's a bit of a mouthful of course, but in most cases MY_CONFIG would be set once
    #  , and before hpi runs, so hopefully it's not a huge deal
    cfg_dir = tmp_path / 'my'
    cfg_file = cfg_dir / 'config.py'
    cfg_dir.mkdir()

    cfg_file.write_text(
        f'''
# print("IMPORTING CONFIG {run_id}")
class demo:
    username = 'xxx_{run_id}'
    data_path = r'{tmp_path}{os.sep}*.json'  # need raw string for windows...
'''
    )

    with tmp_environ_set('MY_CONFIG', str(tmp_path)):
        [item1, item2] = items()
        assert item1.username == f'xxx_{run_id}'
        assert item2.username == f'xxx_{run_id}'

        # sigh.. so this is cached in sys.path
        #  so it takes precedence later during next import, not giving the MY_CONFIG hook
        #  (imported from builtin my.config) to kick in
        sys.path.remove(str(tmp_path))

        # FIXME ideally this shouldn't be necessary?
        #  remove this after we fixup my.tests.reddit and my.tests.commits
        #  (they were failing ci when running all tests)
        sys.modules.pop('my.config', None)


@pytest.fixture(autouse=True)
def prepare_data(tmp_path: Path):
    (tmp_path / 'data.json').write_text(
        '''
[
    {"key": 1, "value": 123},
    {"key": 2, "value": 456}
]
'''
    )
