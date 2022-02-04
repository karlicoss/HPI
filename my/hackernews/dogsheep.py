"""
Hackernews data via Dogsheep [[hacker-news-to-sqlite][https://github.com/dogsheep/hacker-news-to-sqlite]]
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Sequence, Optional, Dict


from my.config import hackernews as user_config


from ..core import Paths
@dataclass
class config(user_config.dogsheep):
    # paths[s]/glob to the dogsheep database
    export_path: Paths


# todo so much boilerplate... really need some common wildcard imports?...
# at least for stuff which realistically is used in each module like get_files/Sequence/Paths/dataclass/Iterator/Optional
from ..core import get_files
from pathlib import Path
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


from .common import hackernews_link

# TODO not sure if worth splitting into Comment and Story?
@dataclass(unsafe_hash=True)
class Item:
    id: str
    type: str
    # TODO is it urc??
    created: datetime
    title: Optional[str]  # only present for Story
    text_html: Optional[str] # should be present for Comment and might for Story
    url: Optional[str] # might be present for Story
    # todo process 'deleted'? fields?
    # todo process 'parent'?

    @property
    def permalink(self) -> str:
        return hackernews_link(self.id)


from ..core.error import Res
from ..core.dataset import connect_readonly
def items() -> Iterator[Res[Item]]:
    f = max(inputs())
    with connect_readonly(f) as db:
        items = db['items']
        for r in items.all(order_by='time'):
            yield Item(
                id=r['id'],
                type=r['type'],
                created=datetime.fromtimestamp(r['time']),
                title=r['title'],
                # todo hmm maybe a method to stip off html tags would be nice
                text_html=r['text'],
                url=r['url'],
            )
