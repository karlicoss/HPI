import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path

from my.config import codeforces as config  # type: ignore[attr-defined]
from my.core import Res, datetime_aware, get_files


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


ContestId = int


@dataclass
class Contest:
    contest_id: ContestId
    when: datetime_aware
    name: str


@dataclass
class Competition:
    contest: Contest
    old_rating: int
    new_rating: int

    @cached_property
    def when(self) -> datetime_aware:
        return self.contest.when


# todo not sure if parser is the best name? hmm
class Parser:
    def __init__(self, *, inputs: Sequence[Path]) -> None:
        self.inputs = inputs
        self.contests: dict[ContestId, Contest] = {}

    def _parse_allcontests(self, p: Path) -> Iterator[Contest]:
        j = json.loads(p.read_text())
        for c in j['result']:
            yield Contest(
                contest_id=c['id'],
                when=datetime.fromtimestamp(c['startTimeSeconds'], tz=timezone.utc),
                name=c['name'],
            )

    def _parse_competitions(self, p: Path) -> Iterator[Competition]:
        j = json.loads(p.read_text())
        for c in j['result']:
            contest_id = c['contestId']
            contest = self.contests[contest_id]
            yield Competition(
                contest=contest,
                old_rating=c['oldRating'],
                new_rating=c['newRating'],
            )

    def parse(self) -> Iterator[Res[Competition]]:
        for path in inputs():
            if 'allcontests' in path.name:
                # these contain information about all CF contests along with useful metadata
                for contest in self._parse_allcontests(path):
                    # TODO some method to assert on mismatch if it exists? not sure
                    self.contests[contest.contest_id] = contest
            elif 'codeforces' in path.name:
                # these contain only contests the user participated in
                yield from self._parse_competitions(path)
            else:
                raise RuntimeError(f"shouldn't happen: {path.name}")


def data() -> Iterator[Res[Competition]]:
    return Parser(inputs=inputs()).parse()
