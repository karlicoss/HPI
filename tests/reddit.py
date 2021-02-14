from .common import skip_if_not_karlicoss as pytestmark

from datetime import datetime
import pytz

from my.common import make_dict


def test() -> None:
    from my.reddit import events, inputs, saved
    list(events())
    list(saved())


def test_unfav() -> None:
    from my.reddit import events, inputs, saved
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
    from my.reddit import events, inputs, saved
    # TODO not sure if this is necesasry anymore?
    saves = list(saved())
    # just check that they are unique..
    make_dict(saves, key=lambda s: s.sid)


def test_disappearing() -> None:
    from my.reddit import events, inputs, saved
    # eh. so for instance, 'metro line colors' is missing from reddit-20190402005024.json for no reason
    # but I guess it was just a short glitch... so whatever
    saves = events()
    favs = [s.kind for s in saves if s.text == 'favorited']
    [deal_with_it] = [f for f in favs if f.title == '"Deal with it!"']
    assert deal_with_it.backup_dt == datetime(2019, 4, 1, 23, 10, 25, tzinfo=pytz.utc)


def test_unfavorite() -> None:
    from my.reddit import events, inputs, saved
    evs = events()
    unfavs = [s for s in evs if s.text == 'unfavorited']
    [xxx] = [u for u in unfavs if u.eid == 'unf-19ifop']
    assert xxx.dt == datetime(2019, 1, 28, 8, 10, 20, tzinfo=pytz.utc)


def test_extra_attr() -> None:
    from my.reddit import config
    assert isinstance(getattr(config, 'passthrough'), str)


import pytest # type: ignore
@pytest.fixture(autouse=True, scope='module')
def prepare():
    from my.common import get_files
    from my.config import reddit as config
    files = get_files(config.export_path)
    # use less files for the test to make it faster
    # first bit is for 'test_unfavorite, the second is for test_disappearing
    files = files[300:330] + files[500:520]
    config.export_dir = files # type: ignore

    setattr(config, 'passthrough', "isn't handled, but available dynamically nevertheless")
