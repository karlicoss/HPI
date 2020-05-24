from itertools import chain

from more_itertools import unique_everseen

from ..core import warn_if_empty

@warn_if_empty
def merge_tweets(*sources):
    yield from unique_everseen(
        chain(*sources),
        key=lambda t: t.id_str,
    )
