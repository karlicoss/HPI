'''
Stackexchange data (uses API via [[https://github.com/karlicoss/stexport][stexport]])
'''
REQUIRES = [
    'git+https://github.com/karlicoss/stexport',
]

from dataclasses import dataclass

from stexport import dal

from my.core import (
    PathIsh,
    Stats,
    get_files,
    make_config,
    stat,
)

import my.config  # isort: skip


@dataclass
class stackexchange(my.config.stackexchange):
    '''
    Uses [[https://github.com/karlicoss/stexport][stexport]] outputs
    '''

    export_path: PathIsh


config = make_config(stackexchange)
# TODO kinda annoying it's resolving gdpr path here (and fails during make_config if gdpr path isn't available)
# I guess it's a good argument to avoid clumping configs together
# or move to my.config.stackexchange.stexport
###


# todo lru cache?
def _dal() -> dal.DAL:
    inputs = get_files(config.export_path)
    return dal.DAL(inputs)


# TODO not sure if should keep the sites separate.. probably easier to filter after than merge
def site(name: str) -> dal.SiteDAL:
    return _dal().site_dal(name)


def stats() -> Stats:
    res = {}
    for name in _dal().sites():
        s = site(name=name)
        res.update({name: stat(s.questions, name='questions')})
    return res
