#!/usr/bin/env python3
from itertools import islice

from my.core.cachew import disable_cachew
disable_cachew()

import my.location.takeout as LT
from my.kython.kompress import kopen


def ilen(it):
    # TODO more_itertools?
    return len(list(it))


def test_location_perf():
    # 2.80 s for 10 iterations and 10K points
    # TODO try switching to jq and see how it goes? not sure..
    print(ilen(islice(LT.iter_locations(), 0, 10000)))


def test_parser():
    from my.kython.ktakeout import TakeoutHTMLParser
    from my.takeout import get_last_takeout

    # 4s for parsing with HTMLParser (30K results)
    path = 'Takeout/My Activity/Chrome/MyActivity.html'
    tpath = get_last_takeout(path=path)

    results = []
    def cb(dt, url, title):
        results.append((dt, url, title))

    parser = TakeoutHTMLParser(cb)

    with kopen(tpath, path) as fo:
        dd = fo.read().decode('utf8')
        parser.feed(dd)
    print(len(results))


def parse_takeout_xmllint(data: str):
    # without xmllint (splitting by '<div class="content-cell' -- 0.68 secs)
    # with xmllint -- 2 seconds
    # using html.parser -- 4 seconds (+ all the parsing etc)
    # not *that* much opportunity to speedup I guess
    # the only downside is that html.parser isn't iterative.. might be able to hack with some iternal hacks?
    # wonder what's the bottleneck..
    #
    from subprocess import Popen, PIPE, run
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
