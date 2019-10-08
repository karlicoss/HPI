from functools import lru_cache
from pathlib import Path

from . import paths
from .common import import_file

# from . import my_configuration # import hypexport_model as hypexport

import my_configuration.hypexport_model as hypexport

"""
First way:
 import my_configuration.hypexport_model as hypexport
 works, but my_configuration is scattered across the repository?

Second way:
 from . import my_configuration?
 doesn't seem to work with subpackages?
 right, perhaps symlinking is a good idea after all?...
"""


"""
First alternative:
 @lru_cache()
 def hypexport():
     ... import_file

 ---
 doesn't really work either..
 hypexport = import_file(Path(paths.hypexport.repo) / 'model.py')
 ---

 + TODO check pytest friendliness if some paths are missing? Wonder if still easier to control by manually excluding...
 - not mypy/pylint friendly at all?

Second:
 symlinks and direct import?

 + TODO
 - TODO ????
 ? keeping a symlink to model.py is not much worse than harding path. so it's ok I guess

"""

def get_model() -> hypexport.Model:
    export_dir = Path(paths.hypexport.export_dir)
    sources = list(sorted(export_dir.glob('*.json')))
    model = hypexport.Model(sources)
    return model


Annotation = hypexport.Annotation


from typing import Dict, List, NamedTuple, Optional, Sequence
from pathlib import Path
from datetime import datetime

from .common import group_by_key, the, cproperty


class Page(NamedTuple):
    """
    Represents annotated page along with the annotations
    """
    annotations: Sequence[Annotation]

    @cproperty
    def link(self):
        return the(h.link for h in self.annotations)

    @cproperty
    def title(self):
        return the(h.title for h in self.annotations)

    @cproperty
    def dt(self) -> datetime:
        return min(h.dt for h in self.annotations)


def _iter():
    yield from get_model().iter_annotations()


def get_pages() -> List[Page]:
    grouped = group_by_key(_iter(), key=lambda e: e.link)
    pages = []
    for link, group in grouped.items():
        sgroup = tuple(sorted(group, key=lambda e: e.dt))
        pages.append(Page(annotations=sgroup))
    pages = list(sorted(pages, key=lambda p: p.dt))
    # TODO fixme page tag??
    return pages


def get_highlights():
    return list(_iter())


def test():
    get_pages()
    get_highlights()


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()
