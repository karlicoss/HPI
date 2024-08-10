from my.config import topcoder as config  # type: ignore[attr-defined]


from dataclasses import dataclass
from functools import cached_property
import json
from pathlib import Path
from typing import Iterator, Sequence

from my.core import get_files, Res, datetime_aware
from my.core.compat import fromisoformat, NoneType


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

    @cached_property
    def summary(self) -> str:
        return f'participated in {self.contest}: {self.percentile:.0f}'

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
    j = json.loads(p.read_text())

    # this is kind of an experiment to parse it exhaustively, making sure we don't miss any data
    assert isinstance(j.pop('version'), str)
    assert isinstance(j.pop('id'), str)
    [j] = j.values()  # zoom in

    assert j.pop('success') is True, j
    assert j.pop('status') == 200, j
    assert j.pop('metadata') is None, j
    [j] = j.values()  # zoom in

    # todo hmm, potentially error handling could be nicer since .pop just reports key error
    # also by the time error is reported, key is already removed?
    for k in ['handle', 'handleLower', 'userId', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy']:
        # check it's primitive
        assert isinstance(j.pop(k), (str, bool, float, int, NoneType)), k

    j.pop('DEVELOP')  # TODO how to handle it?
    [j] = j.values()  # zoom in, DATA_SCIENCE section

    mm = j.pop('MARATHON_MATCH')
    [mm] = mm.values()  # zoom into historu

    srm = j.pop('SRM')
    [srm] = srm.values()  # zoom into history

    assert len(j) == 0, j

    for c in mm + srm:
        yield from Competition.make(j=c)


def data() -> Iterator[Res[Competition]]:
    *_, last = inputs()
    return _parse_one(last)
