"""
Helper 'module' for test_guess_stats
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence


@dataclass
class Item:
    id: str
    dt: datetime
    source: Path


def inputs() -> Sequence[Path]:
    return [
        Path('file1.json'),
        Path('file2.json'),
        Path('file3.json'),
    ]


def iter_data() -> Iterable[Item]:
    dt = datetime.fromisoformat('2020-01-01 01:01:01')
    for path in inputs():
        for i in range(3):
            yield Item(id=str(i), dt=dt + timedelta(days=i), source=path)
