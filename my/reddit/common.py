"""
This defines Protocol classes, which make sure that each different
type of shared models have a standardized interface
"""

from my.core import __NOT_HPI_MODULE__  # isort: skip

from collections.abc import Iterator
from itertools import chain
from typing import Protocol

from my.core import Json, datetime_aware


# common fields across all the Protocol classes, so generic code can be written
class RedditBase(Protocol):
    @property
    def raw(self) -> Json: ...
    @property
    def created(self) -> datetime_aware: ...
    @property
    def id(self) -> str: ...
    @property
    def url(self) -> str: ...
    @property
    def text(self) -> str: ...


# Note: doesn't include GDPR Save's since they don't have the same metadata
class Save(RedditBase, Protocol):
    @property
    def subreddit(self) -> str: ...

# Note: doesn't include GDPR Upvote's since they don't have the same metadata
class Upvote(RedditBase, Protocol):
    @property
    def title(self) -> str: ...


# From rexport, pushshift and the reddit GDPR export
class Comment(RedditBase, Protocol):
    pass


# From rexport and the GDPR export
class Submission(RedditBase, Protocol):
    @property
    def title(self) -> str: ...


def _merge_comments(*sources: Iterator[Comment]) -> Iterator[Comment]:
    #from .rexport import logger
    #ignored = 0
    emitted: set[str] = set()
    for e in chain(*sources):
        uid = e.id
        if uid in emitted:
            #ignored += 1
            #logger.info('ignoring %s: %s', uid, e)
            continue
        yield e
        emitted.add(uid)
    #logger.info(f"Ignored {ignored} comments...")

