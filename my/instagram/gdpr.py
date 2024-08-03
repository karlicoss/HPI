"""
Instagram data (uses [[https://www.instagram.com/download/request][official GDPR export]])
"""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Iterator, Sequence, Dict, Union

from more_itertools import bucket

from my.core import (
    get_files,
    Paths,
    datetime_naive,
    Res,
    assert_never,
    make_logger,
)
from my.core.common import unique_everseen

from my.config import instagram as user_config


logger = make_logger(__name__)


@dataclass
class config(user_config.gdpr):
    # paths[s]/glob to the exported zip archives
    export_path: Paths
    # TODO later also support unpacked directories?


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


# TODO think about unifying with stuff from android.py
@dataclass(unsafe_hash=True)
class User:
    id: str
    username: str
    full_name: str


@dataclass
class _BaseMessage:
    # ugh, this is insane, but does look like it's just keeping local device time???
    # checked against a message sent on 3 June, which should be UTC+1, but timestamp seems local
    created: datetime_naive
    text: str
    thread_id: str
    # NOTE: doesn't look like there aren't any meaningful message ids in the export


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    user_id: str


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    user: User


def _decode(s: str) -> str:
    # yeah... idk why they do that
    return s.encode('latin-1').decode('utf8')


def _entities() -> Iterator[Res[Union[User, _Message]]]:
    # it's worth processing all previous export -- sometimes instagram removes some metadata from newer ones
    # NOTE: here there are basically two options
    # - process inputs as is (from oldest to newest)
    #   this would be more stable wrt newer exports (e.g. existing thread ids won't change)
    #   the downside is that newer exports seem to have better thread ids, so might be preferrable to use them
    # - process inputs reversed (from newest to oldest)
    #   the upside is that thread ids/usernames might be better
    #   the downside is that if for example the user renames, thread ids will change _a lot_, might be undesirable..
    # (from newest to oldest)
    for path in inputs():
        yield from _entitites_from_path(path)


def _entitites_from_path(path: Path) -> Iterator[Res[Union[User, _Message]]]:
    # TODO make sure it works both with plan directory
    # idelaly get_files should return the right thing, and we won't have to force ZipPath/match_structure here
    # e.g. possible options are:
    # - if packed things are detected, just return ZipPath
    # - if packed things are detected, possibly return match_structure_wrapper
    #   it might be a bit tricky because it's a context manager -- who will recycle it?
    # - if unpacked things are detected, just return the dir as it is
    #   (possibly detect them via match_structure? e.g. what if we have a bunch of unpacked dirs)
    #
    # I guess the goal for core.structure module was to pass it to other functions that expect unpacked structure
    # https://github.com/karlicoss/HPI/pull/175
    # whereas here I don't need it..
    # so for now will just implement this adhoc thing and think about properly fixing later

    personal_info = path / 'personal_information'
    if not personal_info.exists():
        # old path, used up to somewhere between feb-aug 2022
        personal_info = path / 'account_information'

    personal_info_json = personal_info / 'personal_information.json'
    if not personal_info_json.exists():
        # new path, started somewhere around april 2024
        personal_info_json = personal_info / 'personal_information' / 'personal_information.json'

    j = json.loads(personal_info_json.read_text())
    [profile] = j['profile_user']
    pdata = profile['string_map_data']
    username = pdata['Username']['value']
    full_name = _decode(pdata['Name']['value'])

    # just make up something :shrug:
    self_id = username
    self_user = User(
        id=self_id,
        username=username,
        full_name=full_name,
    )
    yield self_user

    files = list(path.rglob('messages/inbox/*/message_*.json'))
    assert len(files) > 0, path

    buckets = bucket(files, key=lambda p: p.parts[-2])
    file_map = {k: list(buckets[k]) for k in buckets}

    for fname, ffiles in file_map.items():
        for ffile in sorted(ffiles, key=lambda p: int(p.stem.split('_')[-1])):
            logger.info(f'{ffile} : processing...')
            j = json.loads(ffile.read_text())

            id_len = 10
            # NOTE: I'm not actually sure it's other user's id.., since it corresponds to the whole converstation
            # but I stared a bit at these ids vs database ids and can't see any way to find the correspondence :(
            # so basically the only way to merge is to actually try some magic and correlate timestamps/message texts?
            # another option is perhaps to query user id from username with some free API
            # it's still fragile: e.g. if user deletes themselves there is no more username (it becomes "instagramuser")
            # if we use older exports we might be able to figure it out though... so think about it?
            # it also names grouped ones like instagramuserchrisfoodishblogand25others_einihreoog
            # so I feel like there is just not guaranteed way to correlate :(
            other_id = fname[-id_len:]
            # NOTE: no match in android db?
            other_username = fname[: -id_len - 1]
            other_full_name = _decode(j['title'])
            yield User(
                id=other_id,
                username=other_username,
                full_name=other_full_name,
            )

            # todo "thread_type": "Regular" ?
            for jm in reversed(j['messages']):  # in json, they are in reverse order for some reason
                try:
                    content = None
                    if 'content' in jm:
                        content = _decode(jm['content'])
                        if content.endswith(' to your message '):
                            # ugh. for some reason these contain an extra space and that messes up message merging..
                            content = content.strip()
                    else:
                        if (share := jm.get('share')) is not None:
                            if (share_link := share.get('link')) is not None:
                                # somewhere around 20231007, instagram removed these from gdpr links and they show up a lot in various diffs
                                share_link = share_link.replace('feed_type=reshare_chaining&', '')
                                share_link = share_link.replace('?feed_type=reshare_chaining', '')
                                share['link'] = share_link
                            if (share_text := share.get('share_text')) is not None:
                                share['share_text'] = _decode(share_text)

                        photos = jm.get('photos')
                        videos = jm.get('videos')
                        cc = share or photos or videos
                        if cc is not None:
                            content = str(cc)

                    if content is None:
                        # this happens e.g. on reel shares..
                        # not sure what we can do properly, GPDR has literally no other info in this case
                        # on android in this case at the moment we have as content ''
                        # so for consistency let's do that too
                        content = ''

                    timestamp_ms = jm['timestamp_ms']
                    sender_name = _decode(jm['sender_name'])

                    user_id = other_id if sender_name == other_full_name else self_id
                    yield _Message(
                        created=datetime.fromtimestamp(timestamp_ms / 1000),
                        text=content,
                        user_id=user_id,
                        thread_id=fname,  # meh.. but no better way?
                    )
                except Exception as e:
                    yield e


# TODO basically copy pasted from android.py... hmm
def messages() -> Iterator[Res[Message]]:
    id2user: Dict[str, User] = {}
    for x in unique_everseen(_entities):
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, User):
            id2user[x.id] = x
            continue
        if isinstance(x, _Message):
            try:
                user = id2user[x.user_id]
            except Exception as e:
                yield e
                continue
            yield Message(
                created=x.created,
                text=x.text,
                thread_id=x.thread_id,
                user=user,
            )
            continue
        assert_never(x)
