from my.core import __NOT_HPI_MODULE__  # isort: skip

from collections.abc import Iterator
from itertools import chain
from typing import Any

from more_itertools import unique_everseen

# TODO add proper Protocol for Tweet
Tweet = Any
TweetId = str


from my.core import Res, warn_if_empty


@warn_if_empty
def merge_tweets(*sources: Iterator[Res[Tweet]]) -> Iterator[Res[Tweet]]:
    def key(r: Res[Tweet]):
        if isinstance(r, Exception):
            return str(r)
        else:
            # using both fields as key makes it a bit easier to spot TZ issues
            return (r.id_str, r.created_at)
    yield from unique_everseen(chain(*sources), key=key)


def permalink(*, screen_name: str, id: str) -> str:  # noqa: A002
    return f'https://twitter.com/{screen_name}/status/{id}'

# NOTE: tweets from archive are coming sorted by created_at
# NOTE: tweets from twint are also sorted by created_at?
