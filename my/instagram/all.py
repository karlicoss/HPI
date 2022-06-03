from typing import Iterator

from my.core import Res, stat, Stats
from my.core.source import import_source

from .common import Message, _merge_messages


src_gdpr = import_source(module_name='my.instagram.gdpr')
@src_gdpr
def _messages_gdpr() -> Iterator[Res[Message]]:
    from . import gdpr
    yield from gdpr.messages()


src_android = import_source(module_name='my.instagram.android')
@src_android
def _messages_android() -> Iterator[Res[Message]]:
    from . import android
    yield from android.messages()


def messages() -> Iterator[Res[Message]]:
    # TODO in general best to prefer android, it has more data
    # but for now prefer gdpr prefix until we figure out how to correlate conversation threads
    yield from _merge_messages(
        _messages_gdpr(),
        _messages_android(),
    )


def stats() -> Stats:
    return stat(messages)
