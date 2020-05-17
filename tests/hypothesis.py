#!/usr/bin/env python3

from my.hypothesis import pages, highlights

def test():
    assert len(list(pages())) > 10
    assert len(list(highlights())) > 10
