"""
[[https://uk.kobobooks.com/products/kobo-aura-one][Kobo]] e-ink reader: annotations and reading stats
"""

REQUIRES = [
    'kobuddy',
]


from .core import Paths, dataclass
from my.config import kobo as user_config
@dataclass
class kobo(user_config):
    '''
    Uses [[https://github.com/karlicoss/kobuddy#as-a-backup-tool][kobuddy]] outputs.
    '''
    # path[s]/glob to the exported databases
    export_path: Paths


from .core.cfg import make_config
config = make_config(kobo)

from .core import get_files
import kobuddy
# todo not sure about this glob..
kobuddy.DATABASES = list(get_files(config.export_path, glob='*.sqlite'))

#########################

# hmm, explicit imports make pylint a bit happier?
from kobuddy import Highlight, get_highlights
from kobuddy import *



from .core import stat, Stats
def stats() -> Stats:
    return stat(get_highlights)

## TODO hmm. not sure if all this really belongs here?... perhaps orger?


from typing import Callable, Union, List
# TODO maybe type over T?
_Predicate = Callable[[str], bool]
Predicatish = Union[str, _Predicate]
def from_predicatish(p: Predicatish) -> _Predicate:
    if isinstance(p, str):
        def ff(s):
            return s == p
        return ff
    else:
        return p


def by_annotation(predicatish: Predicatish, **kwargs) -> List[Highlight]:
    pred = from_predicatish(predicatish)

    res: List[Highlight] = []
    for h in get_highlights(**kwargs):
        if pred(h.annotation):
            res.append(h)
    return res


def get_todos() -> List[Highlight]:
    def with_todo(ann):
        if ann is None:
            ann = ''
        return 'todo' in ann.lower().split()
    return by_annotation(with_todo)


def test_todos() -> None:
    todos = get_todos()
    assert len(todos) > 3
