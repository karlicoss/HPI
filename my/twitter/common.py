from itertools import chain

from more_itertools import unique_everseen


def merge_tweets(*sources):
    yield from unique_everseen(
        chain(*sources),
        key=lambda t: t.id_str,
    )
