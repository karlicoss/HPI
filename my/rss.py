from itertools import chain
from typing import List, Dict

from ._rss import Subscription

from . import feedbin
from . import feedly
# TODO google reader?


def get_all_subscriptions() -> List[Subscription]:
    """
    Keeps track of everything I ever subscribed to. It's useful to keep track of unsubscribed too
    so you don't try to subscribe again (or at least take into account why you unsubscribed before)
    """
    states = {}
    states.update(feedly.get_states())
    states.update(feedbin.get_states())
    by_url: Dict[str, Subscription] = {}
    for d, feeds in sorted(states.items()):
        for f in feeds:
            if f.url not in by_url:
                by_url[f.url] = f
    res = []
    last = {x.url: x for x in max(states.items())[1]}
    for u, x in sorted(by_url.items()):
        present = u in last
        res.append(x._replace(subscribed=present))
    return res
