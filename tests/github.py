#!/usr/bin/env python3
from more_itertools import ilen

from my.coding.github import get_events

# todo test against stats? not sure.. maybe both

def test_gdpr():
    import my.github.gdpr as gdpr
    assert ilen(gdpr.events()) > 100


def test():
    events = get_events()
    assert ilen(events) > 100
    for e in events:
        print(e)
