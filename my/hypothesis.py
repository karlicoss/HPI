from typing import Dict, List, NamedTuple, Optional, Sequence
from pathlib import Path
from datetime import datetime

from .common import group_by_key, the, cproperty, PathIsh

from my_configuration import paths
import my_configuration.repos.hypexport.model as hypexport

class Config(NamedTuple):
    export_path_: Optional[PathIsh]=None
    hypexport_path_: Optional[PathIsh]=None

    @property
    def export_path(self) -> Path:
        ep = self.export_path_
        if ep is not None:
            return Path(ep)
        else:
            from my_configuration import paths
            return Path(paths.hypothesis.export_path)

    @property
    def hypexport(self):
        hp = self.hypexport_path_
        if hp is not None:
            raise RuntimeError("TODO")
        else:
            import my_configuration.repos.hypexport.model as hypexport
            return hypexport

config = Config()
def configure(*, export_path: Optional[PathIsh]=None, hypexport_path: Optional[PathIsh]=None) -> None:
    # TODO kwargs?
    global config
    config = Config(
        export_path_=export_path,
        hypexport_path_=hypexport_path,
    )

# TODO for the purposes of mypy, try importing my_configuration anyway?
# return type for this method as well
# TODO check if it works at runtime..
def get_model() -> hypexport.Model:
    export_path = config.export_path
    sources = list(sorted(export_path.glob('*.json')))
    model = hypexport.Model(sources)
    return model


Highlight = hypexport.Highlight


class Page(NamedTuple):
    """
    Represents annotated page along with the highlights
    """
    highlights: Sequence[Highlight]

    @cproperty
    def link(self):
        return the(h.page_link for h in self.highlights)

    @cproperty
    def title(self):
        return the(h.page_title for h in self.highlights)

    @cproperty
    def dt(self) -> datetime:
        return min(h.dt for h in self.highlights)


def _iter():
    yield from get_model().iter_highlights()


def get_pages() -> List[Page]:
    grouped = group_by_key(_iter(), key=lambda e: e.page_link)
    pages = []
    for link, group in grouped.items():
        sgroup = tuple(sorted(group, key=lambda e: e.dt))
        pages.append(Page(highlights=sgroup))
    pages = list(sorted(pages, key=lambda p: p.dt))
    # TODO fixme page tag??
    return pages


def get_highlights():
    return list(sorted(_iter(), key=lambda h: h.dt))


def test():
    get_pages()
    get_highlights()


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()
