from datetime import datetime
import json
from typing import NamedTuple, Iterator, Dict, Union, Sequence

from my_configuration import paths


class Favorite(NamedTuple):
    dt: datetime
    text: str


Res = Union[Favorite, Exception]


def parse_fav(j: Dict) -> Favorite:
    a = j['attachments']
    # TODO unpack?
    return Favorite(
        dt=datetime.utcfromtimestamp(j['date']),
        text=j['text'],
    )

def _iter_favs() -> Iterator[Res]:
    jj = json.loads(paths.vk.favs_file.read_text())
    for j in jj:
        try:
            yield parse_fav(j)
        except Exception as e:
            yield e


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
