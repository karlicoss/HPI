from collections.abc import Iterator

from my.core import Res, Stats, stat
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
    # - message ids
    # - usernames are correct for Android data
    # - thread ids more meaningful?
    # but for now prefer gdpr prefix since it makes a bit things a bit more consistent?
    # e.g. a new batch of android exports can throw off ids if we rely on it for mapping
    yield from _merge_messages(
        _messages_gdpr(),
        _messages_android(),
    )


def stats() -> Stats:
    return stat(messages)
