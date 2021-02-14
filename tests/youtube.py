# TODO move elsewhere?
# these tests would only make sense with some existing data? although some of them would work for everyone..
# not sure what's a good way of handling this..
from .common import skip_if_not_karlicoss as pytestmark

# TODO ugh. if i uncomment this here (on top level), then this test vvv fails
# from my.media.youtube import get_watched, Watched
# HPI_TESTS_KARLICOSS=true pytest -raps tests/tz.py tests/youtube.py

def test() -> None:
    from my.media.youtube import get_watched, Watched
    watched = list(get_watched())
    assert len(watched) > 1000

    from datetime import datetime
    import pytz
    w = Watched(
        url='https://www.youtube.com/watch?v=hTGJfRPLe08',
        title='Jamie xx - Gosh',
        when=datetime(year=2018, month=6, day=21, hour=5, minute=48, second=34, tzinfo=pytz.utc),
    )
    assert w in watched
