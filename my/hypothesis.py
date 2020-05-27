"""
[[https://hypothes.is][Hypothes.is]] highlights and annotations
"""
from dataclasses import dataclass
from typing import Optional

from .core import Paths, PathIsh

from my.config import hypothesis as user_config


@dataclass
class hypothesis(user_config):
    '''
    Uses [[https://github.com/karlicoss/hypexport][hypexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths

    # path to a local clone of hypexport
    # alternatively, you can put the repository (or a symlink) in $MY_CONFIG/my/config/repos/hypexport
    hypexport  : Optional[PathIsh] = None

    @property
    def dal_module(self):
        rpath = self.hypexport
        if rpath is not None:
            from .core.common import import_dir
            return import_dir(rpath, '.dal')
        else:
            import my.config.repos.hypexport.dal as dal
            return dal


from .core.cfg import make_config
config = make_config(hypothesis)


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import my.config.repos.hypexport.dal as dal
else:
    dal = config.dal_module

############################

from typing import List
from .core.error import Res, sort_res_by

Highlight = dal.Highlight
Page      = dal.Page


def _dal() -> dal.DAL:
    from .core import get_files
    sources = get_files(config.export_path)
    return dal.DAL(sources)


def highlights() -> List[Res[Highlight]]:
    return sort_res_by(_dal().highlights(), key=lambda h: h.created)


# TODO eh. always provide iterators? although sort_res_by could be neat too...
def pages() -> List[Res[Page]]:
    return sort_res_by(_dal().pages(), key=lambda h: h.created)


# todo not public api yet
def stats():
    # todo add 'last date' checks et
    return {
        # todo ilen
        'highlights': len(highlights()),
        'pages'     : len(pages()),
    }


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()

get_highlights = highlights # TODO deprecate
get_pages = pages # TODO deprecate
