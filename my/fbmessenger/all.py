from collections.abc import Iterator

from my.core import Res, Stats
from my.core.source import import_source

from .common import Message, _merge_messages

src_export  = import_source(module_name='my.fbmessenger.export')
src_android = import_source(module_name='my.fbmessenger.android')


@src_export
def _messages_export() -> Iterator[Res[Message]]:
    from . import export
    # ok, this one is a little tricky
    # export.Message type is actually external (coming from fbmessengerexport module)
    # so it's unclear how to make mypy believe/check that common.Message is a structural subtype of export.Message
    # we could use runtime_checkable, but then it might also crash in runtime
    # which feels somewhat mean if someone is only using fmbessenger.export module and needs its attributes only
    # so perhaps it makes sense that the typecheck belongs here?
    for m in export.messages():
        # NOTE: just 'yield m' works and seems to type check properly
        if isinstance(m, Exception):
            yield m
        else:
            # however, this way it results in a nicer error (shows the missing Protocol attributes)
            # https://github.com/python/mypy/issues/8235#issuecomment-570712356
            m2: Message = m
            yield m2


@src_android
def _messages_android() -> Iterator[Res[Message]]:
    from . import android
    yield from android.messages()


def messages() -> Iterator[Res[Message]]:
    yield from _merge_messages(
        _messages_export(),
        _messages_android(),
    )


def stats() -> Stats:
    from my.core import stat
    return stat(messages)
