#!/usr/bin/env python3
from more_itertools import ilen

from my.coding.github import get_events, iter_gdpr_events


def test_gdpr():
    assert ilen(iter_gdpr_events()) > 100


def test():
    events = get_events()
    assert len(events) > 100
    for e in events:
        print(e)
