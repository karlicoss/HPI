#!/usr/bin/env python3
from my.coding.github import get_events

def test():
    events = get_events()
    assert len(events) > 100
    for e in events:
        print(e)
