#!/usr/bin/env python3
import csv
import json
from typing import Iterator, List, NamedTuple

from ..paths import BACKUPS


BDIR = BACKUPS / 'imdb'


def get_last():
    # TODO wonder where did json come from..
    return max(BDIR.glob('*.csv'))


class Movie(NamedTuple):
    created: str
    title: str
    rating: int


def iter_movies() -> Iterator[Movie]:
    last = get_last()

    with last.open() as fo:
        reader = csv.DictReader(fo)
        for i, line in enumerate(reader):
            # print(line)
            # id_ = "n" + str(i)
            title = line['Title']
            rating = line['You rated']
            created = line['created']
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
