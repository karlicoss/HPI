from my.core import __NOT_HPI_MODULE__

from datetime import datetime
from typing import Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from typing import Protocol
    except ImportError:
        # requirement of mypy
        from typing_extensions import Protocol  # type: ignore[misc]
else:
    Protocol = object


class Thread(Protocol):
    @property
    def id(self) -> str: ...

    # todo hmm it doesn't like it because one from .export is just str, not Optional...
    # name: Optional[str]


class Message(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def dt(self) -> datetime: ...

    @property
    def text(self) -> Optional[str]: ...

    @property
    def thread(self) -> Thread: ...


from itertools import chain
from more_itertools import unique_everseen
from my.core import warn_if_empty, Res

@warn_if_empty
def _merge_messages(*sources: Iterator[Res[Message]]) -> Iterator[Res[Message]]:
    # todo might be nice to dump some stats for debugging, e.g. how many were overlapping?
    def key(r: Res[Message]):
        if isinstance(r, Exception):
            return str(r)
        else:
            return r.id
    yield from unique_everseen(chain(*sources), key=key)
