"""
Instagram data (uses [[https://www.instagram.com/download/request][official GDPR export]])
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from more_itertools import bucket, spy

from my.core import (
    Json,
    Paths,
    Res,
    assert_never,
    datetime_naive,
    get_files,
    make_logger,
)
from my.core.common import unique_everseen
from my.core.compat import add_note

from my.config import instagram as user_config  # isort: skip

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
    # NOTE: doesn't look like there are any meaningful message ids in the export


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    user_id: str


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    user: User


def _decode(s: str) -> str:
    # yeah... idk why they do that
    return s.encode('latin-1').decode('utf8')


def _entities() -> Iterator[Res[User | _Message]]:
    # it's worth processing all previous export -- sometimes instagram removes some metadata from newer ones
    # NOTE: here there are basically two options
    # - process inputs as is (from oldest to newest)
    #   this would be more stable wrt newer exports (e.g. existing thread ids won't change)
    #   the downside is that newer exports seem to have better thread ids, so might be preferable to use them
    # - process inputs reversed (from newest to oldest)
    #   the upside is that thread ids/usernames might be better
    #   the downside is that if for example the user renames, thread ids will change _a lot_, might be undesirable..
    # (from newest to oldest)
    for path in inputs():
        yield from _entitites_from_path(path)


def _entitites_from_path(path: Path) -> Iterator[Res[User | _Message]]:
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

    self_user = User(
        id=username,  # there is no actual id in gdpr export.. so just make up something :shrug:
        username=username,
        full_name=full_name,
    )
    yield self_user

    files = sorted(path.rglob('messages/inbox/*/message_*.json'))  # sort for more determinism
    assert len(files) > 0, path

    # parts[-2] is the directory name, which contains username/user id
    buckets = bucket(files, key=lambda p: p.parts[-2])
    conversation_to_message_files = {k: list(buckets[k]) for k in buckets}

    for conversation, message_files in conversation_to_message_files.items():

        def iter_jsons() -> Iterator[Json]:
            # messages are in files like message_1, message_2, etc -- order them by that number
            for message_file in sorted(message_files, key=lambda p: int(p.stem.split('_')[-1])):
                logger.info(f'{message_file} : processing...')
                yield json.loads(message_file.read_text())

        (first,), jsons = spy(iter_jsons())
        # title should be the same across all files, so enough to extract only first
        conversation_title = _decode(first['title'])

        # TODO older gdpr exports had 10 alnum characters?? with no relation to server id?
        m = re.fullmatch(r'(.*)_(\d+)', conversation)
        assert m is not None

        # NOTE: conversaion_username is kinda frafile
        #   e.g. if user deletes themselves there is no more username (it becomes "instagramuser")
        #   if we use older exports we might be able to figure it out though... so think about it?
        #   it also names grouped ones like instagramuserchrisfoodishblogand25others_einihreoog
        conversation_username = m.group(1)

        # NOTE: same as in android database!
        thread_v2_id = m.group(2)

        # NOTE: I'm not actually sure it's other user's id.., since it corresponds to the whole conversation
        # but I stared a bit at these ids vs database ids and can't see any way to find the correspondence :(
        # so basically the only way to merge is to actually try some magic and correlate timestamps/message texts?
        # another option is perhaps to query user id from username with some free API
        # so I feel like there is just not guaranteed way to correlate :(
        other_user = User(
            id=conversation_username,  # again, no actual ids in gdrp, so just make something up
            username=conversation_username,
            full_name=conversation_title,
        )
        yield other_user

        def _parse_message(jm: Json) -> _Message:
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

            user_id = other_user.id if sender_name == conversation_title else self_user.id
            return _Message(
                created=datetime.fromtimestamp(timestamp_ms / 1000),
                text=content,
                user_id=user_id,
                thread_id=thread_v2_id,
            )

        for j in jsons:
            # todo "thread_type": "Regular" ?
            for jm in reversed(j['messages']):  # in json, they are in reverse order for some reason
                try:
                    yield _parse_message(jm)
                except Exception as e:
                    add_note(e, f'^ while parsing {jm}')
                    yield e


# TODO basically copy pasted from android.py... hmm
def messages() -> Iterator[Res[Message]]:
    id2user: dict[str, User] = {}
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
                add_note(e, f'^ while processing {x}')
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
