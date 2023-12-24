"""
Twitter data from offficial app for Android
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from struct import unpack_from
from typing import Iterator, Sequence

from my.core import datetime_aware, get_files, LazyLogger, Paths, Res
from my.core.common import unique_everseen
from my.core.sqlite import sqlite_connect_immutable

import my.config

from .common import permalink

logger = LazyLogger(__name__)


@dataclass
class config(my.config.twitter.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@dataclass(unsafe_hash=True)
class Tweet:
    id_str: str
    created_at: datetime_aware
    screen_name: str
    text: str

    @property
    def permalink(self) -> str:
        return permalink(screen_name=self.screen_name, id=self.id_str)


def _parse_content(data: bytes) -> str:
    pos = 0

    def skip(count: int) -> None:
        nonlocal pos
        pos += count

    def getstring(slen: int) -> str:
        if slen == 1:
            lfmt = '>B'
        elif slen == 2:
            lfmt = '>H'
        else:
            raise RuntimeError

        (sz,) = unpack_from(lfmt, data, offset=pos)
        skip(slen)
        assert sz > 0
        assert sz <= 10000  # sanity check?

        # soo, this is how it should ideally work:
        # (ss,) = unpack_from(f'{sz}s', data, offset=pos)
        # skip(sz)
        # however sometimes there is a discrepancy between string length in header and actual length (if you stare at the data)
        # example is 1725868458246570412
        # wtf??? (see logging below)

        # ughhhh
        seps = [
            b'I\x08',
            b'I\x09',
        ]
        sep_idxs = [data[pos:].find(sep) for sep in seps]
        sep_idxs = [i for i in sep_idxs if i != -1]
        assert len(sep_idxs) > 0
        sep_idx = min(sep_idxs)

        # print("EXPECTED LEN", sz, "GOT", sep_idx, "DIFF", sep_idx - sz)

        zz = data[pos : pos + sep_idx]
        skip(sep_idx)
        return zz.decode('utf8')

    skip(2)  # always starts with 4a03?

    (xx,) = unpack_from('B', data, offset=pos)
    skip(1)
    # print("TYPE:", xx)

    # wtf is this... maybe it's a bitmask?
    slen = {
        66 : 1,
        67 : 2,
        106: 1,
        107: 2,
    }[xx]

    text = getstring(slen=slen)

    # after the main tweet text it contains entities (e.g. shortened urls)
    # however couldn't reverse engineer the schema properly, the links are kinda all over the place

    # TODO this also contains image alt descriptions?
    # see 1665029077034565633

    extracted = []
    linksep = 0x6a
    while True:
        m = re.search(b'\x6a.http', data[pos:])
        if m is None:
            break

        qq = m.start()
        pos += qq

        while True:
            if data[pos] != linksep:
                break
            pos += 1
            (sz,) = unpack_from('B', data, offset=pos)
            pos += 1
            (ss,) = unpack_from(f'{sz}s', data, offset=pos)
            pos += sz
            extracted.append(ss)

    replacements = {}
    i = 0
    while i < len(extracted):
        if b'https://t.co/' in extracted[i]:
            key = extracted[i].decode('utf8')
            value = extracted[i + 1].decode('utf8')
            i += 2
            replacements[key] = value
        else:
            i += 1

    for k, v in replacements.items():
        text = text.replace(k, v)
    assert 'https://t.co/' not in text  # make sure we detected all links

    return text


def _process_one(f: Path) -> Iterator[Res[Tweet]]:
    with sqlite_connect_immutable(f) as db:
        # NOTE:
        # - it also has statuses_r_ent_content which has entities' links replaced
        #   but they are still ellipsized (e.g. check 1692905005479580039)
        #   so let's just uses statuses_content
        # - there is also timeline_created_at, but they look like made up timestamps
        #   don't think they represent bookmarking time
        # - not sure what's timeline_type?
        #   seems like 30 means bookmarks?
        #   there is one tweet with timeline type 18, but it has timeline_is_preview=1
        for (
            tweet_id,
            user_name,
            user_username,
            created_ms,
            blob,
        ) in db.execute(
            '''
            SELECT
            statuses_status_id,
            users_name,
            users_username,
            statuses_created,
            CAST(statuses_content AS BLOB)
            FROM timeline_view
            WHERE statuses_bookmarked = 1
            ORDER BY timeline_sort_index DESC
            ''',
        ):
            if blob is None:  # TODO exclude in sql query?
                continue
            yield Tweet(
                id_str=tweet_id,
                # TODO double check it's utc?
                created_at=datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc),
                screen_name=user_username,
                text=_parse_content(blob),
            )


def bookmarks() -> Iterator[Res[Tweet]]:
    # TODO might need to sort by timeline_sort_index again?
    # not sure if each database contains full history of bookmarks (likely not!)
    def it() -> Iterator[Res[Tweet]]:
        paths = inputs()
        total = len(paths)
        width = len(str(total))
        for idx, path in enumerate(paths):
            logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
            yield from _process_one(path)

    # TODO hmm maybe unique_everseen should be a decorator?
    return unique_everseen(it)
