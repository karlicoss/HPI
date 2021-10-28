from typing import Iterator, Any, Callable, TypeVar
from my.core.source import import_source_iter as imp

from .common import Save, Upvote, Comment, Submission, _merge_comments

# Man... ideally an all.py file isn't this verbose, but
# reddit just feels like that much of a complicated source and
# data acquired by different methods isn't the same

### import helpers

# this import error is caught in import_source_iter, if rexport isn't installed
def _rexport_import() -> Any:
    from . import rexport as source
    return source

def _rexport_comments() -> Iterator[Comment]:
    yield from imp(_rexport_import().comments)

def _pushshift_import() -> Any:
    from . import pushshift as source
    return source

def _pushshift_comments() -> Iterator[Comment]:
    yield from imp(_pushshift_import().comments)

# Merged functions

def comments() -> Iterator[Comment]:
    # TODO: merge gdpr here
    yield from _merge_comments(_rexport_comments(), _pushshift_comments())

def submissions() -> Iterator[Submission]:
    # TODO: merge gdpr here
    yield from imp(lambda: _rexport_import().submissions())

def saved() -> Iterator[Save]:
    yield from imp(lambda: _rexport_import().saved())

def upvoted() -> Iterator[Upvote]:
    yield from imp(lambda: _rexport_import().upvoted())

def stats() -> Stats:
    from my.core import stat
    return {
        **stat(saved),
        **stat(comments),
        **stat(submissions),
        **stat(upvoted),
    }

