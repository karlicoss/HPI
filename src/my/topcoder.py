import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from my.core import Res, datetime_aware, get_files
from my.core.compat import fromisoformat
from my.experimental.destructive_parsing import Manager

from my.config import topcoder as config  # type: ignore[attr-defined]  # isort: skip


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@dataclass
class Competition:
    contest_id: str
    contest: str
    percentile: float
    date_str: str

    @cached_property
    def uid(self) -> str:
        return self.contest_id

    @cached_property
    def when(self) -> datetime_aware:
        return fromisoformat(self.date_str)

    @classmethod
    def make(cls, j) -> Iterator[Res['Competition']]:
        assert isinstance(j.pop('rating'), float)
        assert isinstance(j.pop('placement'), int)

        cid = j.pop('challengeId')
        cname = j.pop('challengeName')
        percentile = j.pop('percentile')
        date_str = j.pop('date')

        yield cls(
            contest_id=cid,
            contest=cname,
            percentile=percentile,
            date_str=date_str,
        )


def _parse_one(p: Path) -> Iterator[Res[Competition]]:
    d = json.loads(p.read_text())

    # TODO manager should be a context manager?
    m = Manager()

    h = m.helper(d)
    h.pop_if_primitive('version', 'id')

    h = h.zoom('result')
    h.check('success', expected=True)
    h.check('status', 200)
    h.pop_if_primitive('metadata')

    h = h.zoom('content')
    h.pop_if_primitive('handle', 'handleLower', 'userId', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy')

    # NOTE at the moment it's empty for me, but it will result in an error later if there is some data here
    h.zoom('DEVELOP').zoom('subTracks')

    h = h.zoom('DATA_SCIENCE')
    # TODO multi zoom? not sure which axis, e.g.
    # zoom('SRM', 'history') or zoom('SRM', 'MARATHON_MATCH')
    # or zoom(('SRM', 'history'), ('MARATHON_MATCH', 'history'))
    srms = h.zoom('SRM').zoom('history')
    mms = h.zoom('MARATHON_MATCH').zoom('history')

    for c in srms.item + mms.item:
        # NOTE: so here we are actually just using pure dicts in .make method
        # this is kinda ok since it will be checked by parent Helper
        # but also expects cooperation from .make method (e.g. popping items from the dict)
        # could also wrap in helper and pass to .make .. not sure
        # an argument could be made that .make isn't really a class methond..
        # it's pretty specific to this parser only
        yield from Competition.make(j=c)

    yield from m.check()


def data() -> Iterator[Res[Competition]]:
    *_, last = inputs()
    return _parse_one(last)
