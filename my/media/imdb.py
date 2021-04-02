#!/usr/bin/env python3
import csv
from datetime import datetime
from typing import Iterator, List, NamedTuple

from ..common import get_files

from my.config import imdb as config

def _get_last():
    return max(get_files(config.export_path, glob='*.csv'))


class Movie(NamedTuple):
    created: datetime
    title: str
    rating: int


def iter_movies() -> Iterator[Movie]:
    last = _get_last()

    with last.open() as fo:
        reader = csv.DictReader(fo)
        for i, line in enumerate(reader):
            # TODO extract directors??
            title = line['Title']
            rating = int(line['You rated'])
            createds = line['created']
            created = datetime.strptime(createds, '%a %b %d %H:%M:%S %Y')
            # TODO const??
            yield Movie(created=created, title=title, rating=rating)


def get_movies() -> List[Movie]:
    return list(sorted(iter_movies(), key=lambda m: m.created))


def test():
    assert len(get_movies()) > 10


def main():
    for movie in get_movies():
        print(movie)

if __name__ == '__main__':
    main()
