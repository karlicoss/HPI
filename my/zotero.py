from __future__ import annotations as _annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from my.core import Res, datetime_aware, make_logger
from my.core.sqlite import sqlite_copy_and_open

logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    db = Path('~').expanduser() / 'Zotero' / 'zotero.sqlite'
    # todo eh... kinda pointless to return a list in this case... but maybe ok for consistency?
    # also naming the method input() will conflict with python builtin...
    return [db]


Url = str

@dataclass(frozen=True)
class Item:
    """Corresponds to 'Zotero item'"""
    file: Path
    title: str
    url: Url | None
    tags: Sequence[str]


@dataclass
class Annotation:
    item: Item
    added: datetime_aware
    # checked it and it's definitely utc

    page: int
    """0-indexed"""

    text: str | None
    comment: str | None
    tags: Sequence[str]
    color_hex: str
    """Original hex-encoded color in zotero"""

    @property
    def color_human(self) -> str:
        return _hex2human(self.color_hex)


def annotations() -> Iterator[Res[Annotation]]:
    for r in _query_raw():
        if isinstance(r, Exception):
            yield r
            continue
        try:
            a = _parse_annotation(r)
            yield a
        except Exception as e:
            yield e


# type -- 1 is inline; 2 is note?
_QUERY = '''
SELECT A.itemID, A.parentItemID, F.parentItemID AS topItemID, text, comment, color, position, path, dateAdded
FROM itemAnnotations AS A
LEFT JOIN itemAttachments AS F ON A.parentItemID = F.ItemID
LEFT JOIN items AS I           ON A.itemID = I.itemID
'''


_QUERY_TAGS = '''
SELECT name
FROM itemTags AS IT
LEFT JOIN tags as T ON IT.tagID = T.tagID
WHERE itemID = ?
'''.strip()


_QUERY_TITLE = '''
SELECT value AS title
FROM itemData AS ID
LEFT JOIN itemDataValues AS IDV ON ID.valueID == IDV.valueID
WHERE ID.fieldID = 1 AND itemID = ?
'''.strip()


_QUERY_URL = '''
SELECT value AS url FROM
itemData AS ID
LEFT JOIN itemDataValues  AS IDV ON ID.valueID == IDV.valueID
LEFT JOIN itemAttachments AS IA  ON ID.itemID  == IA.parentItemID
WHERE ID.fieldID = 13 AND IA.itemID = ?
'''.strip()


# TODO maybe exclude 'private' methods from detection?
def _query_raw() -> Iterator[Res[dict[str, Any]]]:
    [db] = inputs()

    with sqlite_copy_and_open(db) as conn:
        conn.row_factory = sqlite3.Row
        for r in conn.execute(_QUERY):
            try:
                yield _enrich_row(r, conn=conn)
            except Exception as e:
                logger.exception(e)
                ex = RuntimeError(f'Error while processing {list(r)}')
                ex.__cause__ = e
                yield ex
    conn.close()


# the data mode in zotero database seems as follows..
#
# itemAnnotations
# - itemId is the annotation itself
# - parentItemId is the PDF file, corresponds to itemAttachments.itemId??
#
# itemAttachments
# - itemId
# - parentItemId is just the 'abstract' top level item in zotero
#   this top level item is the one that shows up in the file list? ugh also some indirection in itemNotes...
#

def _enrich_row(r, conn: sqlite3.Connection):
    r = dict(r)
    # TODO very messy -- would be nice to do this with less queries
    # tags are annoying... because they are in one-to-many relationship, hard to retrieve in sqlite..
    iid = r['itemID']
    tags = [row[0] for row in conn.execute(_QUERY_TAGS, [iid])]
    r['tags'] = tuple(tags)

    topid = r['topItemID']
    top_tags = [row[0] for row in conn.execute(_QUERY_TAGS, [topid])]
    r['top_tags'] = tuple(top_tags)

    pid = r['parentItemID']
    [title] = [row[0] for row in conn.execute(_QUERY_TITLE, [pid])]
    r['title'] = title

    murl = [row[0] for row in conn.execute(_QUERY_URL, [pid])]
    url = None if len(murl) == 0 else murl[0]
    r['url'] = url
    return r


def _hex2human(color_hex: str) -> str:
    return {
        '#ffd400': 'yellow',
        '#a28ae5': 'purple',
        '#5fb236': 'green' ,
        '#ff6666': 'red'   ,
        '#2ea8e5': 'blue'  ,
    }.get(color_hex, color_hex)


def _parse_annotation(r: dict) -> Annotation:
    text     = r['text']
    comment  = r['comment']
    # todo use json query for this?
    page = json.loads(r['position'])['pageIndex']
    path     = r['path']
    addeds   = r['dateAdded']
    tags     = r['tags']
    color_hex= r['color']

    added = datetime.strptime(addeds, '%Y-%m-%d %H:%M:%S')
    added = added.replace(tzinfo=timezone.utc)

    item = Item(
        file=Path(path),  # path is a bit misleading... could mean some internal DOM path?
        title=r['title'],
        url=r['url'],
        tags=r['top_tags']
    )

    return Annotation(
        item=item,
        added=added,
        page=page,
        text=text,
        comment=comment,
        tags=tags,
        color_hex=color_hex,
    )
