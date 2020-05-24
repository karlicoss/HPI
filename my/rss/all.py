'''
Unified RSS data, merged from different services I used historically
'''
# NOTE: you can comment out the sources you're not using
from . import feedbin, feedly

from typing import Iterable
from .common import Subscription, compute_subscriptions


def subscriptions() -> Iterable[Subscription]:
    # TODO google reader?
    yield from compute_subscriptions(
        feedbin.states(),
        feedly .states(),
    )
