"""
Various helpers for reading org-mode data
"""

from datetime import datetime


def parse_org_datetime(s: str) -> datetime:
    s = s.strip('[]')
    for fmt, _cls in [
        ("%Y-%m-%d %a %H:%M", datetime),
        ("%Y-%m-%d %H:%M"   , datetime),
        # todo not sure about these... fallback on 00:00?
        # ("%Y-%m-%d %a"      , date),
        # ("%Y-%m-%d"         , date),
    ]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise RuntimeError(f"Bad datetime string {s}")


# TODO I guess want to borrow inspiration from bs4? element type <-> tag; and similar logic for find_one, find_all

from collections.abc import Iterable
from typing import Callable, TypeVar

from orgparse import OrgNode

V = TypeVar('V')


def collect(n: OrgNode, cfun: Callable[[OrgNode], Iterable[V]]) -> Iterable[V]:
    yield from cfun(n)
    for c in n.children:
        yield from collect(c, cfun)


from more_itertools import one
from orgparse.extra import Table


def one_table(o: OrgNode) -> Table:
    return one(collect(o, lambda n: (x for x in n.body_rich if isinstance(x, Table))))


class TypedTable(Table):
    def __new__(cls, orig: Table) -> 'TypedTable':
        tt = super().__new__(TypedTable)
        tt.__dict__ = orig.__dict__
        blocks = list(orig.blocks)
        header = blocks[0]  # fist block is schema
        if len(header) == 2:
            # TODO later interpret first line as types
            header = header[1:]
        setattr(tt, '_blocks', [header, *blocks[1:]])
        return tt

    @property
    def blocks(self):
        return getattr(self, '_blocks')
