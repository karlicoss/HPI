from functools import lru_cache
from pathlib import Path

from . import paths

@lru_cache()
def hypexport():
    from .common import import_file
    return import_file(Path(paths.hypexport.repo) / 'model.py')

def get_model():
    export_dir = Path(paths.hypexport.export_dir)
    sources = list(sorted(export_dir.glob('*.json')))
    model = hypexport().Model(sources)
    return model


Annotation = hypexport().Annotation


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


# TODO is it even necessary?
def get_entries():
    return list(_iter())


def get_todos():
    def is_todo(e: Annotation) -> bool:
        if any(t.lower() == 'todo' for t in  e.tags):
            return True
        if e.text is None:
            return False
        return e.text.lstrip().lower().startswith('todo')
    return list(filter(is_todo, get_entries()))


def test():
    get_pages()
    get_todos()
    get_entries()


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()
