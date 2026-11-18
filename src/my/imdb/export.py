"""
IMDb ratings from legacy CSV exports.

Reads the older ``Title``, ``You rated``, and ``created`` columns.
See https://help.imdb.com/article/imdb/featured-content/ratings-faq/G67Y87TFYYP6TWAV for the CSV export feature.
"""

import csv
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from my.core import Paths, Stats, datetime_naive, get_files, stat


class config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs for legacy IMDb CSV exports; the last path in filename order is used."""
        raise NotImplementedError


def make_config() -> config:
    from my.config import imdb as user_config

    class combined_config(user_config, config):
        pass

    return combined_config()


def _get_last() -> Path:
    return max(get_files(make_config().export_path))


class Movie(NamedTuple):
    created: datetime_naive
    title: str
    rating: int


def iter_movies() -> Iterator[Movie]:
    last = _get_last()

    with last.open(newline='') as fo:
        reader = csv.DictReader(fo)
        for line in reader:
            # TODO extract directors??
            title = line['Title']
            rating = int(line['You rated'])
            createds = line['created']
            created = datetime.strptime(createds, '%a %b %d %H:%M:%S %Y')
            # TODO const??
            yield Movie(created=created, title=title, rating=rating)


def stats() -> Stats:
    return stat(iter_movies)
