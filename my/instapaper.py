"""
[[https://www.instapaper.com][Instapaper]] bookmarks, highlights and annotations
"""
REQUIRES = [
    'git+https://github.com/karlicoss/instapexport',
]

from dataclasses import dataclass

from my.config import instapaper as user_config

from .core import Paths


@dataclass
class instapaper(user_config):
    '''
    Uses [[https://github.com/karlicoss/instapexport][instapexport]] outputs.
    '''
    # path[s]/glob to the exported JSON data
    export_path : Paths


from .core.cfg import make_config

config = make_config(instapaper)


try:
    from instapexport import dal
except ModuleNotFoundError as e:
    from my.core.hpi_compat import pre_pip_dal_handler

    dal = pre_pip_dal_handler('instapexport', e, config, requires=REQUIRES)

############################

Highlight = dal.Highlight
Bookmark  = dal.Bookmark
Page      = dal.Page


from collections.abc import Iterable, Sequence
from pathlib import Path

from .core import get_files


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def pages() -> Iterable[Page]:
    return _dal().pages()


def stats():
    from .core import stat
    return stat(pages)

### misc

# TODO dunno, move this to private?
def is_todo(hl: Highlight) -> bool:
    note = hl.note or ''
    note = note.lstrip().lower()
    return note.startswith('todo')


get_pages = pages # todo also deprecate..
