"""
Various helpers for reading org-mode data
"""

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Self

from more_itertools import one
from orgparse import OrgNode
from orgparse.extra import Table


def parse_org_datetime(s: str) -> datetime:
    s = s.strip('[]')
    for fmt, _cls in [
        ("%Y-%m-%d %a %H:%M", datetime),
        ("%Y-%m-%d %H:%M"   , datetime),
        # todo not sure about these... fallback on 00:00?
        # ("%Y-%m-%d %a"      , date),
        # ("%Y-%m-%d"         , date),
    ]:  # fmt: skip
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise RuntimeError(f"Bad datetime string {s}")


# TODO I guess want to borrow inspiration from bs4? element type <-> tag; and similar logic for find_one, find_all


def collect[V](n: OrgNode, cfun: Callable[[OrgNode], Iterable[V]]) -> Iterable[V]:
    yield from cfun(n)
    for c in n.children:
        yield from collect(c, cfun)


def one_table(o: OrgNode) -> Table:
    return one(collect(o, lambda n: (x for x in n.body_rich if isinstance(x, Table))))


class TypedTable(Table):
    def __new__(cls, orig: Table) -> Self:
        tt = super().__new__(cls)
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
