from itertools import chain

from more_itertools import unique_everseen

from ..core import warn_if_empty, __NOT_HPI_MODULE__

@warn_if_empty
def merge_tweets(*sources):
    yield from unique_everseen(
        chain(*sources),
        key=lambda t: t.id_str,
    )
