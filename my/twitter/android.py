"""
Twitter data from official app for Android
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
    # NOTE: individual databases are very patchy.
    # e.g. some contain hundreds of my bookmarks, whereas other contain just a few
    # good motivation for synthetic exports
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


_SELECT_OWN_TWEETS = '_SELECT_OWN_TWEETS'


def get_own_user_id(conn) -> str:
    # unclear what's the reliable way to query it, so we use multiple different ones and arbitrate
    # NOTE: 'SELECT DISTINCT ev_owner_id FROM lists' doesn't work, might include lists from other people?
    res = set()
    for q in [
        'SELECT DISTINCT list_mapping_user_id FROM list_mapping',
        'SELECT DISTINCT owner_id FROM cursors',
        'SELECT DISTINCT user_id FROM users WHERE _id == 1',
    ]:
        for (r,) in conn.execute(q):
            res.add(r)
    assert len(res) == 1, res
    return str(list(res)[0])


# NOTE:
# - it also has statuses_r_ent_content which has entities' links replaced
#   but they are still ellipsized (e.g. check 1692905005479580039)
#   so let's just uses statuses_content
# - there is also timeline_created_at, but they look like made up timestamps
#   don't think they represent bookmarking time
# - timeline_type
#   7, 8, 9: some sort of notifications or cursors, should exclude
#   17: ??? some cursors but also tweets
#   18: ??? relatively few, maybe 20 of them, also they all have timeline_is_preview=1?
#       most of them have our own id as timeline_sender?
#       I think it might actually be 'replies' tab -- also contains some retweets etc
#   26: ??? very low sort index
#   28: weird, contains lots of our own tweets, but also a bunch of unrelated..
#   29: seems like it contains the favorites!
#   30: seems like it contains the bookmarks
#   34: contains some tweets -- not sure..
#   63: contains the bulk of data
#   69: ??? just a few tweets
# - timeline_data_type
#   1 : the bulk of tweets, but also some notifications etc??
#   2 : who-to-follow/community-to-join. contains a couple of tweets, but their corresponding status_id is NULL
#   8 : who-to-follow/notfication
#   13: semantic-core/who-to-follow
#   14: cursor
#   17: trends
#   27: notification
#   31: some superhero crap
#   37: semantic-core
#   42: community-to-join
# - timeline_entity_type
#   1 : contains the bulk of data -- either tweet-*/promoted-tweet-*. However some notification-* and some just contain raw ids??
#   11: some sort of 'superhero-superhero' crap
#   13: always cursors
#   15: tweet-*/tweet:*/home-conversation-*/trends-*/and lots of other crap
#   31: always notification-*
# - timeline_data_type_group
#   0 : tweets?
#   6 : always notifications??
#   42: tweets (bulk of them)
def _process_one(f: Path, *, where: str) -> Iterator[Res[Tweet]]:
    with sqlite_connect_immutable(f) as db:
        if _SELECT_OWN_TWEETS in where:
            own_user_id = get_own_user_id(db)
            where = where.replace(_SELECT_OWN_TWEETS, own_user_id)

        for (
            tweet_id,
            user_name,
            user_username,
            created_ms,
            blob,
        ) in db.execute(
            f'''
            SELECT
            statuses_status_id,
            users_name,
            users_username,
            statuses_created,
            CAST(statuses_content AS BLOB)
            FROM timeline_view
            WHERE timeline_data_type == 1       /* the only one containing tweets (among with some other stuff) */
              AND timeline_data_type_group != 6 /* excludes notifications (some of them even have statuses_bookmarked == 1) */
              AND {where}
            ORDER BY timeline_sort_index DESC
            ''',
            # TODO not sure about timeline_sort_index for favorites
        ):
            assert blob is not None  # just in case, but should be filtered by the sql query
            yield Tweet(
                id_str=tweet_id,
                # TODO double check it's utc?
                created_at=datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc),
                screen_name=user_username,
                text=_parse_content(blob),
            )


def _entities(*, where: str) -> Iterator[Res[Tweet]]:
    # TODO might need to sort by timeline_sort_index again?
    def it() -> Iterator[Res[Tweet]]:
        paths = inputs()
        total = len(paths)
        width = len(str(total))
        for idx, path in enumerate(paths):
            logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
            yield from _process_one(path, where=where)

    # TODO hmm maybe unique_everseen should be a decorator?
    return unique_everseen(it)


def bookmarks() -> Iterator[Res[Tweet]]:
    # NOTE: in principle we get the bulk of bookmarks via timeline_type == 30 filter
    # however we still might miss on a few (I think the timeline_type 30 only refreshes when you enter bookmarks in the app)
    # if you bookmarked in the home feed, it might end up as status_bookmarked == 1 but not necessarily as timeline_type 30
    return _entities(where='statuses_bookmarked == 1')


def likes() -> Iterator[Res[Tweet]]:
    # NOTE: similarly to bookmarks, we could use timeline_type == 29, but it's only refreshed if we actually open likes tab
    return _entities(where='statuses_favorited == 1')


def tweets() -> Iterator[Res[Tweet]]:
    # NOTE: where timeline_type == 18 covers quite a few of our on tweets, but not everything
    # querying by our own user id seems the most exhaustive
    return _entities(where=f'timeline_sender_id == {_SELECT_OWN_TWEETS}')
