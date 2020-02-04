from datetime import datetime
from pathlib import Path
from itertools import tee
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Sequence, Union, Iterable

from .common import PathIsh, cproperty, group_by_key, the
from .error import Res, sort_res_by


try:
    # TODO might be worth having a special mode for type checking with and without mycfg?
    # TODO could somehow use typing.TYPE_CHECKING for that?
    import mycfg.repos.hypexport.dal as hypexport
    Highlight = hypexport.Highlight
    DAL = hypexport.DAL
    Page = hypexport.Page
except:
    DAL = Any # type: ignore
    Highlight = Any # type: ignore
    Page = Any # type: ignore


# TODO ok, maybe each module has a specially treated config, that magically recieves values?
# so configure method should be kinda automatically derived
# dunno...

class Config(NamedTuple):
    export_path_: Optional[PathIsh]=None
    hypexport_path_: Optional[PathIsh]=None

    @property
    def export_path(self) -> Path:
        ep = self.export_path_
        if ep is not None:
            return Path(ep)
        else:
            from mycfg import paths
            return Path(paths.hypothesis.export_path)

    @property
    def hypexport(self):
        hp = self.hypexport_path_
        if hp is not None:
            # TODO hmmm
            # TODO that doesn't seem to work (PYTHONPATH=src with_my pytest tests/server_test.py::test_query_instapaper)
            # I guess I need to think about it.. shouluud I just rely on mycfg for setting these paths?
            from .common import import_file
            return import_file(Path(hp) / 'dal.py', 'mycfg.repos.hypexport.dal') # TODO meh...
        else:
            global DAL
            global Highlight
            import mycfg.repos.hypexport.dal as hypexport
            # TODO a bit hacky.. not sure how to make it both mypy and runtime safe..
            DAL = hypexport.DAL
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

# TODO for the purposes of mypy, try importing mycfg anyway?
# return type for this method as well
# TODO check if it works at runtime..
def get_dal() -> DAL:
    export_path = config.export_path
    if export_path.is_file():
        sources = [export_path]
    else:
        sources = list(sorted(export_path.glob('*.json'))) # TODO FIXME common thing
    model = config.hypexport.DAL(sources)
    return model


def get_highlights() -> List[Res[Highlight]]:
    return sort_res_by(get_dal().highlights(), key=lambda h: h.created)

# TODO eh. always provide iterators?
def get_pages() -> List[Res[Page]]:
    return sort_res_by(get_dal().pages(), key=lambda h: h.created)


def test():
    get_pages()
    get_highlights()


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()
