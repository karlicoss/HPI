from my.tests.common import skip_if_not_karlicoss as pytestmark  # isort: skip

# TODO move elsewhere?
# these tests would only make sense with some existing data? although some of them would work for everyone..
# not sure what's a good way of handling this..
from datetime import datetime

import pytz
from more_itertools import bucket

# TODO ugh. if i uncomment this here (on top level), then this test vvv fails
# from my.media.youtube import get_watched, Watched
# HPI_TESTS_KARLICOSS=true pytest -raps tests/tz.py tests/youtube.py


def test() -> None:
    from my.youtube.takeout import Watched, watched
    videos = [w for w in watched() if not isinstance(w, Exception)]
    assert len(videos) > 1000

    # results in nicer errors, otherwise annoying to check against thousands of videos
    grouped = bucket(videos, key=lambda w: (w.url, w.title))

    w1 = Watched(
        url='https://www.youtube.com/watch?v=hTGJfRPLe08',
        title='Jamie xx - Gosh',
        when=pytz.timezone('Europe/London').localize(datetime(year=2018, month=6, day=21, hour=6, minute=48, second=34)),
    )
    assert w1 in list(grouped[(w1.url, w1.title)])

    w2 = Watched(
        url='https://www.youtube.com/watch?v=IZ_8b_Ydsv0',
        title='Why LESS Sensitive Tests Might Be Better',
        when=pytz.utc.localize(datetime(year=2021, month=1, day=15, hour=17, minute=54, second=12)),
    )
    assert w2 in list(grouped[(w2.url, w2.title)])
