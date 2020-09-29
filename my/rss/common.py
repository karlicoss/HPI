# shared Rss stuff
from datetime import datetime
from typing import NamedTuple, Optional, List, Dict


class Subscription(NamedTuple):
    title: str
    url: str
    id: str # TODO not sure about it...
    # eh, not all of them got reasonable 'created' time
    created_at: Optional[datetime]
    subscribed: bool=True

from typing import Iterable, Tuple, Sequence

# snapshot of subscriptions at time
SubscriptionState = Tuple[datetime, Sequence[Subscription]]


from ..core import warn_if_empty
@warn_if_empty
def compute_subscriptions(*sources: Iterable[SubscriptionState]) -> List[Subscription]:
    """
    Keeps track of everything I ever subscribed to.
    In addition, keeps track of unsubscribed as well (so you'd remember when and why you unsubscribed)
    """
    from itertools import chain
    states = list(chain.from_iterable(sources))
    # TODO keep 'source'/'provider'/'service' attribute?

    by_url: Dict[str, Subscription] = {}
    # ah. dates are used for sorting
    for when, state in sorted(states):
        # TODO use 'when'?
        for feed in state:
            if feed.url not in by_url:
                by_url[feed.url] = feed

    if len(states) == 0:
        return []

    _, last_state = max(states, key=lambda x: x[0])
    last_urls = {f.url for f in last_state}

    res = []
    for u, x in sorted(by_url.items()):
        present = u in last_urls
        res.append(x._replace(subscribed=present))
    return res

from ..core import __NOT_HPI_MODULE__
