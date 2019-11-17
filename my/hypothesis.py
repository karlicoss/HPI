from typing import Dict, List, NamedTuple, Optional, Sequence, Any
from pathlib import Path
from datetime import datetime

from .common import group_by_key, the, cproperty, PathIsh


try:
    # TODO might be worth having a special mode for type checking with and without my_configuration?
    # TODO could somehow use typing.TYPE_CHECKING for that?
    import my_configuration.repos.hypexport.model as hypexport
    Highlight = hypexport.Highlight
    Model = hypexport.Model
except:
    Model = Any # type: ignore
    Highlight = Any # type: ignore


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
            global Model
            global Highlight
            import my_configuration.repos.hypexport.model as hypexport
            # TODO a bit hacky.. not sure how to make it both mypy and runtime safe..
            Model = hypexport.Model
            Highlight = hypexport.Highlight
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
def get_model() -> Model:
    export_path = config.export_path
    sources = list(sorted(export_path.glob('*.json')))
    model = Model(sources)
    return model


class Page(NamedTuple):
    """
    Represents annotated page along with the highlights
    """
    highlights: Sequence[Highlight]

    @cproperty
    def link(self) -> str:
        return the(h.page_link for h in self.highlights)

    @cproperty
    def title(self) -> str:
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
