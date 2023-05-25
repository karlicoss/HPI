from datetime import datetime, timezone

from my.core.cfg import tmp_config
from my.core.common import make_dict

# todo ugh, it's discovered as a test???
from .common import testdata

import pytest

# deliberately use mixed style imports on the top level and inside the methods to test tmp_config stuff
import my.reddit.rexport as my_reddit_rexport
import my.reddit.all as my_reddit_all


def test_basic() -> None:
    # todo maybe this should call stat or something instead?
    # would ensure reasonable stat implementation as well and less duplication
    # note: deliberately use old module (instead of my.reddit.all) to test bwd compatibility
    from my.reddit import saved, events

    assert len(list(events())) > 0
    assert len(list(saved())) > 0


def test_comments() -> None:
    assert len(list(my_reddit_all.comments())) > 0


def test_unfav() -> None:
    from my.reddit import events

    ev = events()
    url = 'https://reddit.com/r/QuantifiedSelf/comments/acxy1v/personal_dashboard/'
    uev = [e for e in ev if e.url == url]
    assert len(uev) == 2
    ff = uev[0]
    # TODO could recover these from takeout perhaps?
    assert ff.text == 'favorited [initial]'
    uf = uev[1]
    assert uf.text == 'unfavorited'


def test_saves() -> None:
    from my.reddit.all import saved

    saves = list(saved())
    assert len(saves) > 0

    # just check that they are unique (makedict will throw)
    make_dict(saves, key=lambda s: s.sid)


def test_disappearing() -> None:
    # eh. so for instance, 'metro line colors' is missing from reddit-20190402005024.json for no reason
    # but I guess it was just a short glitch... so whatever
    evs = my_reddit_rexport.events()
    favs = [s.kind for s in evs if s.text == 'favorited']
    [deal_with_it] = [f for f in favs if f.title == '"Deal with it!"']
    assert deal_with_it.backup_dt == datetime(2019, 4, 1, 23, 10, 25, tzinfo=timezone.utc)


def test_unfavorite() -> None:
    evs = my_reddit_rexport.events()
    unfavs = [s for s in evs if s.text == 'unfavorited']
    [xxx] = [u for u in unfavs if u.eid == 'unf-19ifop']
    assert xxx.dt == datetime(2019, 1, 29, 10, 10, 20, tzinfo=timezone.utc)


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
