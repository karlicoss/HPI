import pytest
from more_itertools import consume

# deliberately use mixed style imports on the top level and inside the methods to test tmp_config stuff
# todo won't really be necessary once we migrate to lazy user config
import my.reddit.all as my_reddit_all
import my.reddit.rexport as my_reddit_rexport
from my.core.cfg import tmp_config
from my.core.utils.itertools import ensure_unique

from .common import testdata


def test_basic_1() -> None:
    # todo maybe this should call stat or something instead?
    # would ensure reasonable stat implementation as well and less duplication
    # note: deliberately use old module (instead of my.reddit.all) to test bwd compatibility
    from my.reddit import saved

    assert len(list(saved())) > 0


def test_basic_2() -> None:
    # deliberately check call from a different style of import to make sure tmp_config works
    saves = list(my_reddit_rexport.saved())
    assert len(saves) > 0


def test_comments() -> None:
    assert len(list(my_reddit_all.comments())) > 0


def test_saves() -> None:
    from my.reddit.all import saved

    saves = list(saved())
    assert len(saves) > 0

    # will throw if not unique
    consume(ensure_unique(saves, key=lambda s: s.sid))


def test_preserves_extra_attr() -> None:
    # doesn't strictly belong here (not specific to reddit)
    # but my.reddit does a fair bit of dynamic hacking, so perhaps a good place to check nothing is lost
    from my.reddit import config

    assert isinstance(getattr(config, 'please_keep_me'), str)


@pytest.fixture(autouse=True, scope='module')
def prepare():
    data = testdata() / 'hpi-testdata' / 'reddit'
    assert data.exists(), data

    # note: deliberately using old config schema so we can test migrations
    class config:
        class reddit:
            export_dir = data
            please_keep_me = 'whatever'

    with tmp_config(modules='my.reddit.*', config=config):
        yield
