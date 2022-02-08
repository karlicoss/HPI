from my.core import __NOT_HPI_MODULE__

from itertools import chain
from typing import Iterator, Any

from more_itertools import unique_everseen


# TODO add proper Protocol for Tweet
Tweet = Any


from my.core import warn_if_empty, Res
@warn_if_empty
def merge_tweets(*sources: Iterator[Res[Tweet]]) -> Iterator[Res[Tweet]]:
    def key(r: Res[Tweet]):
        if isinstance(r, Exception):
            return str(r)
        else:
            return r.id_str
    yield from unique_everseen(chain(*sources), key=key)
