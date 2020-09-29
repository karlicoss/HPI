"""
[[https://hypothes.is][Hypothes.is]] highlights and annotations
"""
from dataclasses import dataclass
from typing import Optional

from .core import Paths

from my.config import hypothesis as user_config

REQUIRES = [
    'git+https://github.com/karlicoss/hypexport',
]



@dataclass
class hypothesis(user_config):
    '''
    Uses [[https://github.com/karlicoss/hypexport][hypexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths


from .core.cfg import make_config
config = make_config(hypothesis)


try:
    from hypexport import dal
except ModuleNotFoundError as e:
    from .core.compat import pre_pip_dal_handler
    dal = pre_pip_dal_handler('hypexport', e, config, requires=REQUIRES)

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
    from .core import stat
    return {
        **stat(highlights),
        **stat(pages),
    }


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()

get_highlights = highlights # TODO deprecate
get_pages = pages # TODO deprecate
