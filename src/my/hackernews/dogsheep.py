"""
Hackernews data via Dogsheep [[hacker-news-to-sqlite][https://github.com/dogsheep/hacker-news-to-sqlite]]
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import my.config
from my.core import Paths, Res, get_files
from my.core.datetime import AwareDateTime, aware
from my.core.sqlite import sqlite_connection

from .common import hackernews_link


class Config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        '''paths[s]/glob to the dogsheep database'''
        raise NotImplementedError


class config(my.config.hackernews.dogsheep, Config):
    pass


# todo so much boilerplate... really need some common wildcard imports?...
# at least for stuff which realistically is used in each module like get_files/Sequence/Paths/dataclass/Iterator/Optional
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


# TODO not sure if worth splitting into Comment and Story?
@dataclass(unsafe_hash=True)
class Item:
    id: str
    type: str

    # The official Hacker News API defines item.time as its creation date in Unix Time.
    # hacker-news-to-sqlite stores that field unchanged in items.time.
    # - https://github.com/HackerNews/API#items
    # - https://github.com/dogsheep/hacker-news-to-sqlite/blob/c5585c103d124b23ba1e163f8857d4ba49fe452a/hacker_news_to_sqlite/cli.py#L45-L50
    created: AwareDateTime

    title: str | None  # only present for Story
    text_html: str | None  # should be present for Comment and might for Story
    url: str | None  # might be present for Story
    # todo process 'deleted'? fields?
    # todo process 'parent'?

    @property
    def permalink(self) -> str:
        return hackernews_link(self.id)


# TODO hmm kinda annoying that permalink isn't getting serialized
# maybe won't be such a big problem if we used hpi query directly on objects, without jsons?
# so we could just take .permalink thing


def items() -> Iterator[Res[Item]]:
    f = max(inputs())
    with sqlite_connection(f, immutable=True, row_factory='row') as conn:
        for r in conn.execute('SELECT * FROM items ORDER BY time'):
            yield Item(
                id=r['id'],
                type=r['type'],
                created=aware(datetime.fromtimestamp(r['time'], tz=UTC)),
                title=r['title'],
                # todo hmm maybe a method to strip off html tags would be nice
                text_html=r['text'],
                url=r['url'],
            )
