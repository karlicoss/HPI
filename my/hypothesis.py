"""
[[https://hypothes.is][Hypothes.is]] highlights and annotations
"""
from .common import get_files
from .error import Res, sort_res_by

import my.config.repos.hypexport.dal as hypexport
from my.config import hypothesis as config

###

from typing import List


# TODO weird. not sure why e.g. from dal import Highlight doesn't work..
Highlight = hypexport.Highlight
Page      = hypexport.Page


# TODO eh. not sure if I should rename everything to dao/DAO or not...
def _dal() -> hypexport.DAL:
    sources = get_files(config.export_path, '*.json')
    return hypexport.DAL(sources)


def highlights() -> List[Res[Highlight]]:
    return sort_res_by(_dal().highlights(), key=lambda h: h.created)


# TODO eh. always provide iterators? although sort_res_by could be neat too...
def pages() -> List[Res[Page]]:
    return sort_res_by(_dal().pages(), key=lambda h: h.created)


# TODO move to side tests?
def test():
    list(pages())
    list(highlights())


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()

get_highlights = highlights # TODO deprecate
get_pages = pages # TODO deprecate
