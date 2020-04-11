"""
Hypothes.is highlights and annotations
"""
from . import init

from .common import PathIsh

import my.config.repos.hypexport as hypexport
from my.config.repos.hypexport import dal

from my.config import hypothesis as config
export_path: PathIsh = config.export_path

###

from typing import List

from .common import get_files, cproperty, group_by_key
from .error import Res, sort_res_by




# TODO weird. not sure why e.g. from dal import Highlight doesn't work..
Highlight = dal.Highlight
DAL = dal.DAL
Page = dal.Page


# TODO eh. not sure if I should rename everything to dao/DAO or not...
def dao() -> DAL:
    sources = get_files(export_path, '*.json')
    model = DAL(sources)
    return model


def get_highlights() -> List[Res[Highlight]]:
    return sort_res_by(dao().highlights(), key=lambda h: h.created)


# TODO eh. always provide iterators? although sort_res_by could be neat too...
def get_pages() -> List[Res[Page]]:
    return sort_res_by(dao().pages(), key=lambda h: h.created)


# TODO move to side tests?
def test():
    get_pages()
    get_highlights()


def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()
