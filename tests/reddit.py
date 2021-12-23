from datetime import datetime
import pytz


def test_basic() -> None:
    # todo maybe this should call stat or something instead?
    # would ensure reasonable stat implementation as well and less duplication
    # note: deliberately use old module (instead of my.reddit.all) to test bwd compatibility
    from my.reddit import saved, events
    assert len(list(events())) > 0
    assert len(list(saved())) > 0


def test_comments() -> None:
    from my.reddit.all import comments
    assert len(list(comments())) > 0


def test_unfav() -> None:
    from my.reddit import events, saved
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
    from my.core.common import make_dict
    make_dict(saves, key=lambda s: s.sid)


def test_disappearing() -> None:
    from my.reddit.rexport import events
    # eh. so for instance, 'metro line colors' is missing from reddit-20190402005024.json for no reason
    # but I guess it was just a short glitch... so whatever
    saves = events()
    favs = [s.kind for s in saves if s.text == 'favorited']
    [deal_with_it] = [f for f in favs if f.title == '"Deal with it!"']
    assert deal_with_it.backup_dt == datetime(2019, 4, 1, 23, 10, 25, tzinfo=pytz.utc)


def test_unfavorite() -> None:
    from my.reddit.rexport import events
    evs = events()
    unfavs = [s for s in evs if s.text == 'unfavorited']
    [xxx] = [u for u in unfavs if u.eid == 'unf-19ifop']
    assert xxx.dt == datetime(2019, 1, 29, 10, 10, 20, tzinfo=pytz.utc)


def test_preserves_extra_attr() -> None:
    # doesn't strictly belong here (not specific to reddit)
    # but my.reddit does a fair bit of dyunamic hacking, so perhaps a good place to check nothing is lost
    from my.reddit import config
    assert isinstance(getattr(config, 'please_keep_me'), str)


import pytest # type: ignore
@pytest.fixture(autouse=True, scope='module')
def prepare():
    from .common import testdata
    data = testdata() / 'hpi-testdata' / 'reddit'
    assert data.exists(), data

    # note: deliberately using old config schema so we can test migrations
    class test_config:
        export_dir = data
        please_keep_me = 'whatever'

    from my.core.cfg import tmp_config
    with tmp_config() as config:
        config.reddit = test_config
        yield
