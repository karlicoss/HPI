from my.tests.common import skip_if_not_karlicoss as pytestmark  # isort: skip

from datetime import datetime, timezone
from itertools import islice

from more_itertools import ilen

import my.location.google as LT
from my.google.takeout.html import read_html
from my.google.takeout.paths import get_last_takeout


def test_location_perf() -> None:
    # 2.80 s for 10 iterations and 10K points
    # TODO try switching to jq and see how it goes? not sure..
    print(ilen(islice(LT.iter_locations(), 0, 10000)))  # type: ignore[attr-defined]


# in theory should support any HTML takeout file?
# although IIRC bookmarks and search-history.html weren't working
import pytest


@pytest.mark.parametrize(
    'path', [
        'YouTube/history/watch-history.html',
        'My Activity/YouTube/MyActivity.html',
        'My Activity/Chrome/MyActivity.html',
        'My Activity/Search/MyActivity.html',
    ]
)
def test_parser(path: str) -> None:
    path = 'Takeout/' + path
    tpath = get_last_takeout(path=path)
    assert tpath is not None
    results = list(read_html(tpath, path))
    # TODO assert len > 100 or something?
    print(len(results))


def test_myactivity_search() -> None:
    path = 'Takeout/My Activity/Search/MyActivity.html'
    tpath = get_last_takeout(path=path)
    assert tpath is not None
    results = list(read_html(tpath, path))

    res = (
        datetime(year=2018, month=12, day=17, hour=8, minute=16, second=18, tzinfo=timezone.utc),
        'https://en.wikipedia.org/wiki/Emmy_Noether&usg=AFQjCNGrSW-iDnVA2OTcLsG3I80H_a6y_Q',
        'Emmy Noether - Wikipedia',
    )
    assert res in results


def parse_takeout_xmllint(data: str):
    # without xmllint (splitting by '<div class="content-cell' -- 0.68 secs)
    # with xmllint -- 2 seconds
    # using html.parser -- 4 seconds (+ all the parsing etc), 30K results
    # not *that* much opportunity to speedup I guess
    # the only downside is that html.parser isn't iterative.. might be able to hack with some iternal hacks?
    # wonder what's the bottleneck..
    #
    from subprocess import PIPE, Popen, run

    from more_itertools import split_before
    res = run(
        ['xmllint', '--html', '--xpath', '//div[contains(@class, "content-cell")]', '-'],
        input=data.encode('utf8'),
        check=True,
        stdout=PIPE,
    )
    out = res.stdout.decode('utf8')
    # out = data
    return out.split('<div class="content-cell')

from my.google.takeout.html import test_parse_dt
