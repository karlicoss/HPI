"""
Instagram data (uses [[https://www.instagram.com/download/request][official GDPR export]])
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Any, Sequence, Dict

from my.config import instagram as user_config

from more_itertools import bucket

from ..core import Paths
@dataclass
class config(user_config.gdpr):
    # paths[s]/glob to the exported zip archives
    export_path: Paths
    # TODO later also support unpacked directories?


from ..core import get_files
from pathlib import Path
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
    # TODO id is missing?
    created: datetime
    text: str
    thread_id: str


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    user_id: str


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    user: User


def _decode(s: str) -> str:
    # yeah... idk why they do that
    return s.encode('latin-1').decode('utf8')


import json
from typing import Union
from ..core.error import Res
def _entities() -> Iterator[Res[Union[User, _Message]]]:
    from ..core.kompress import ZipPath
    last = ZipPath(max(inputs()))
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

    j = json.loads((last / 'account_information/personal_information.json').read_text())
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

    files = list(last.rglob('messages/inbox/*/message_*.json'))
    assert len(files) > 0, last

    buckets = bucket(files, key=lambda p: p.parts[-2])
    file_map = {k: list(buckets[k]) for k in buckets}

    for fname, ffiles in file_map.items():
        for ffile in sorted(ffiles, key=lambda p: int(p.stem.split('_')[-1])):
            j = json.loads(ffile.read_text())

            id_len = 10
            # NOTE: no match in android db/api responses?
            other_id = fname[-id_len:]
            # NOTE: no match in android db?
            other_username = fname[:-id_len - 1]
            other_full_name = _decode(j['title'])
            yield User(
                id=other_id,
                username=other_username,
                full_name=other_full_name,
            )

            # todo "thread_type": "Regular" ?
            for jm in j['messages']:
                # todo defensive?
                try:
                    mtype = jm['type']  # Generic/Share?
                    content = None
                    if 'content' in jm:
                        content = _decode(jm['content'])
                    else:
                        share  = jm.get('share')
                        photos = jm.get('photos')
                        videos = jm.get('videos')
                        cc = share or photos or videos
                        if cc is not None:
                            content = str(cc)
                    assert content is not None, jm
                    timestamp_ms = jm['timestamp_ms']
                    sender_name = _decode(jm['sender_name'])

                    user_id = other_id if sender_name == other_full_name else self_id
                    yield _Message(
                        created=datetime.fromtimestamp(timestamp_ms / 1000),
                        text=content,
                        user_id=user_id,
                        thread_id=fname, # meh.. but no better way?
                    )
                except Exception as e:
                    # TODO sometimes messages are just missing content?? even with Generic type
                    yield e


# TODO basically copy pasted from android.py... hmm
def messages() -> Iterator[Res[Message]]:
    id2user: Dict[str, User] = {}
    for x in _entities():
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
        assert False, type(x)  # should not happen
