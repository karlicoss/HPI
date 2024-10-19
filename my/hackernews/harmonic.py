"""
[[https://play.google.com/store/apps/details?id=com.simon.harmonichackernews][Harmonic]] app for Hackernews
"""

from __future__ import annotations

REQUIRES = ['lxml', 'orjson']

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast

import orjson
from lxml import etree
from more_itertools import one

import my.config
from my.core import (
    Paths,
    Res,
    Stats,
    datetime_aware,
    get_files,
    make_logger,
    stat,
)
from my.core.common import unique_everseen

from .common import SavedBase, hackernews_link

import my.config  # isort: skip


logger = make_logger(__name__)


@dataclass
class harmonic(my.config.harmonic):
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(harmonic.export_path)


class Cached(TypedDict):
    author: str
    created_at_i: int
    id: str
    points: int
    test: str | None
    title: str
    type: str  # TODO Literal['story', 'comment']? comments are only in 'children' field tho
    url: str
    # TODO also has children with comments, but not sure I need it?


# TODO if we ever add use .text property, need to html.unescape it first
# TODO reuse SavedBase in materialistic?
@dataclass
class Saved(SavedBase):
    raw: Cached

    @property
    def when(self) -> datetime_aware:
        ts = self.raw['created_at_i']
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    @property
    def uid(self) -> str:
        return self.raw['id']

    @property
    def url(self) -> str:
        return self.raw['url']

    @property
    def title(self) -> str:
        return self.raw['title']

    @property
    def hackernews_link(self) -> str:
        return hackernews_link(self.uid)

    def __hash__(self) -> int:
        # meh. but seems like the easiest and fastest way to hash a dict?
        return hash(orjson.dumps(self.raw))


_PREFIX = 'com.simon.harmonichackernews.KEY_SHARED_PREFERENCES'


def _saved() -> Iterator[Res[Saved]]:
    paths = inputs()
    total = len(paths)
    width = len(str(total))
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        # TODO defensive for each item!
        tr = etree.parse(path)

        res = one(cast(list[Any], tr.xpath(f'//*[@name="{_PREFIX}_CACHED_STORIES_STRINGS"]')))
        cached_ids = [x.text.split('-')[0] for x in res]

        cached: dict[str, Cached] = {}
        for sid in cached_ids:
            res = one(cast(list[Any], tr.xpath(f'//*[@name="{_PREFIX}_CACHED_STORY{sid}"]')))
            j = orjson.loads(res.text)
            cached[sid] = j

        res = one(cast(list[Any], tr.xpath(f'//*[@name="{_PREFIX}_BOOKMARKS"]')))
        for x in res.text.split('-'):
            ids, item_timestamp = x.split('q')
            # not sure if timestamp is any useful?

            cc = cached.get(ids, None)
            if cc is None:
                # TODO warn or error?
                continue

            yield Saved(cc)


def saved() -> Iterator[Res[Saved]]:
    yield from unique_everseen(_saved)


def stats() -> Stats:
    return {
        **stat(inputs),
        **stat(saved),
    }
