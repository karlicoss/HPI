from collections.abc import Iterator

from my.core import Stats, stat
from my.core.source import import_source

from .common import Comment, Save, Submission, Upvote, _merge_comments

# Man... ideally an all.py file isn't this verbose, but
# reddit just feels like that much of a complicated source and
# data acquired by different methods isn't the same

### 'safe importers' -- falls back to empty data if the module couldn't be found
rexport_src = import_source(module_name="my.reddit.rexport")
pushshift_src = import_source(module_name="my.reddit.pushshift")

@rexport_src
def _rexport_comments() -> Iterator[Comment]:
    from . import rexport
    yield from rexport.comments()

@rexport_src
def _rexport_submissions() -> Iterator[Submission]:
    from . import rexport
    yield from rexport.submissions()

@rexport_src
def _rexport_saved() -> Iterator[Save]:
    from . import rexport
    yield from rexport.saved()

@rexport_src
def _rexport_upvoted() -> Iterator[Upvote]:
    from . import rexport
    yield from rexport.upvoted()

@pushshift_src
def _pushshift_comments() -> Iterator[Comment]:
    from .pushshift import comments as pcomments
    yield from pcomments()

# Merged functions

def comments() -> Iterator[Comment]:
    # TODO: merge gdpr here
    yield from _merge_comments(_rexport_comments(), _pushshift_comments())

def submissions() -> Iterator[Submission]:
    # TODO: merge gdpr here
    yield from _rexport_submissions()

@rexport_src
def saved() -> Iterator[Save]:
    from .rexport import saved
    yield from saved()

@rexport_src
def upvoted() -> Iterator[Upvote]:
    from .rexport import upvoted
    yield from upvoted()

def stats() -> Stats:
    return {
        **stat(saved),
        **stat(comments),
        **stat(submissions),
        **stat(upvoted),
    }

