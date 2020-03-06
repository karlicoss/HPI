#!/usr/bin/env python3
from my.bluemaestro import measurements, _get_exports


def test():
    print(list(measurements(_get_exports()[-1:])))
