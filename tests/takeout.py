#!/usr/bin/env python3
from itertools import islice

from my.core.cachew import disable_cachew
disable_cachew()

import my.location.takeout as LT


def ilen(it):
    # TODO more_itertools?
    return len(list(it))


def test_location_perf():
    # 2.80 s for 10 iterations and 10K points
    # TODO try switching to jq and see how it goes? not sure..
    print(ilen(islice(LT.iter_locations(), 0, 10000)))
