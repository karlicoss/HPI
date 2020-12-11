# todo: uses my private export script?
from datetime import datetime
import json
from typing import NamedTuple, Iterable, Sequence, Optional

from my.config import vk as config


class Favorite(NamedTuple):
    dt: datetime
    title: str
    url: Optional[str]
    text: str


from ..core import Json
from ..core.error import Res


skip = (
    'graffiti',
    'poll',

    # TODO could be useful..
    'note',
    'doc',
    'audio',
    'photo',
    'album',
    'video',
    'page',
)

def parse_fav(j: Json) -> Favorite:
    # TODO copy_history??
    url = None
    title = '' # TODO ???
    atts = j.get('attachments', [])
    for a in atts:
        if any(k in a for k in skip):
            continue
        link = a['link']
        title = link['title']
        url = link['url']
        #  TODOlink['description'] ?

    # TODO would be nice to include user
    return Favorite(
        dt=datetime.utcfromtimestamp(j['date']),
        title=title,
        url=url,
        text=j['text'],
    )


def _iter_favs() -> Iterable[Res]:
    jj = json.loads(config.favs_file.read_text())
    for j in jj:
        try:
            yield parse_fav(j)
        except Exception as e:
            ex = RuntimeError(f"Error while processing\n{j}")
            ex.__cause__ = e
            yield ex


def favorites() -> Sequence[Res]:
    it = _iter_favs()
    # trick to sort errors along with the actual objects
    # TODO wonder if there is a shorter way?
    # TODO add to the error handling post?
    favs = list(it)
    prev = datetime.min
    keys = []
    for i, f in enumerate(favs):
        if not isinstance(f, Exception):
            prev = f.dt
        keys.append((prev, i)) # include index to resolve ties
    sorted_items = [p[1] for p in sorted(zip(keys, favs))]
    #
    return sorted_items


def stats():
    from ..core import stat
    return stat(favorites)
