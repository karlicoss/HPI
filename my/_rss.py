# shared Rss stuff
from typing import NamedTuple

class Subscription(NamedTuple):
    # TODO date?
    title: str
    url: str
    id: str
    subscribed: bool=True

