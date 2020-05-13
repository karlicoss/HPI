# shared Rss stuff
from datetime import datetime
from typing import NamedTuple, Optional


class Subscription(NamedTuple):
    title: str
    url: str
    id: str # TODO not sure about it...
    # eh, not all of them got reasonable 'created' time
    created_at: Optional[datetime]
    subscribed: bool=True
