"""
[[https://www.instapaper.com][Instapaper]] bookmarks, highlights and annotations
"""
from dataclasses import dataclass
from typing import Optional

from .core import Paths, PathIsh

from my.config import instapaper as user_config


@dataclass
class instapaper(user_config):
    '''
    Uses [[https://github.com/karlicoss/instapexport][instapexport]] outputs.
    '''
    # path[s]/glob to the exported JSON data
    export_path : Paths

    # path to a local clone of instapexport
    # alternatively, you can put the repository (or a symlink) in $MY_CONFIG/my/config/repos/instapexport
    instapexport: Optional[PathIsh] = None

    @property
    def dal_module(self):
        rpath = self.instapexport
        if rpath is not None:
            from .core.common import import_dir
            return import_dir(rpath, '.dal')
        else:
            import my.config.repos.instapexport.dal as dal
            return dal


from .core.cfg import make_config
config = make_config(instapaper)


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import my.config.repos.instapexport.dal as dal
else:
    dal = config.dal_module

############################

Highlight = dal.Highlight
Bookmark  = dal.Bookmark
Page      = dal.Page


from typing import Sequence, Iterable
from pathlib import Path
from .core import get_files
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def pages() -> Iterable[Page]:
    return _dal().pages()


# TODO dunno, move this to private?
def is_todo(hl: Highlight) -> bool:
    note = hl.note or ''
    note = note.lstrip().lower()
    return note.startswith('todo')


get_pages = pages # todo also deprecate..
