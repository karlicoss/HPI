'''
Unified RSS data, merged from different services I used historically
'''
from typing import Iterable
from .common import Subscription, compute_subscriptions


def subscriptions() -> Iterable[Subscription]:
    from . import feedbin, feedly
    # TODO google reader?
    yield from compute_subscriptions(feedbin.states(), feedly.states())
