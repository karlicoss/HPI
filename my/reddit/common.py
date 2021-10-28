"""
This defines Protocol classes, which make sure that each different
type of Comment/Save have a standard interface
"""

from typing import Dict, Any, Set, Iterator
from itertools import chain
from datetime import datetime

Json = Dict[str, Any]

try:
    from typing import Protocol
except ImportError:
    # hmm -- does this need to be installed on 3.6 or is it already here?
    from typing_extensions import Protocol  # type: ignore[misc]

# Note: doesn't include GDPR Save's since they don't have the same metadata
class Save(Protocol):
    created: datetime
    title: str
    raw: Json

    @property
    def sid(self) -> str: ...
    @property
    def url(self) -> str: ...
    @property
    def text(self) -> str: ...
    @property
    def subreddit(self) -> str: ...

# Note: doesn't include GDPR Upvote's since they don't have the same metadata
class Upvote(Protocol):
    raw: Json
    @property
    def created(self) -> datetime: ...
    @property
    def url(self) -> str: ...
    @property
    def text(self) -> str: ...
    @property
    def title(self) -> str: ...


# From rexport, pushshift and the reddit gdpr export
class Comment(Protocol):
    raw: Json
    @property
    def created(self) -> datetime: ...
    @property
    def url(self) -> str: ...
    @property
    def text(self) -> str: ...


# From rexport and the gdpr export
class Submission(Protocol):
    raw: Json
    @property
    def created(self) -> datetime: ...
    @property
    def url(self) -> str: ...
    @property
    def text(self) -> str: ...
    @property
    def title(self) -> str: ...


def _merge_comments(*sources: Iterator[Comment]) -> Iterator[Comment]:
    #from .rexport import logger
    #ignored = 0
    emitted: Set[int] = set()
    for e in chain(*sources):
        key = int(e.raw["created_utc"])
        if key in emitted:
            #ignored += 1
            #logger.info('ignoring %s: %s', key, e)
            continue
        yield e
        emitted.add(key)
    #logger.info(f"Ignored {ignored} comments...")

