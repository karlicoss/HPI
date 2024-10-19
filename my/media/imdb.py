import csv
from collections.abc import Iterator
from datetime import datetime
from typing import NamedTuple

from my.core import get_files

from my.config import imdb as config  # isort: skip


def _get_last():
    return max(get_files(config.export_path))


class Movie(NamedTuple):
    created: datetime
    title: str
    rating: int


def iter_movies() -> Iterator[Movie]:
    last = _get_last()

    with last.open() as fo:
        reader = csv.DictReader(fo)
        for line in reader:
            # TODO extract directors??
            title = line['Title']
            rating = int(line['You rated'])
            createds = line['created']
            created = datetime.strptime(createds, '%a %b %d %H:%M:%S %Y')
            # TODO const??
            yield Movie(created=created, title=title, rating=rating)


def get_movies() -> list[Movie]:
    return sorted(iter_movies(), key=lambda m: m.created)


def test():
    assert len(get_movies()) > 10
