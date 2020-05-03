"""
Instapaper bookmarks, highlights and annotations
"""
from .common import get_files


from my.config import instapaper as config
import my.config.repos.instapexport.dal as dal


Highlight = dal.Highlight
Bookmark = dal.Bookmark


def inputs():
    return get_files(config.export_path)


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def pages():
    return _dal().pages()
get_pages = pages # todo also deprecate..


# TODO dunno, move this to private?
def is_todo(hl: Highlight) -> bool:
    note = hl.note or ''
    note = note.lstrip().lower()
    return note.startswith('todo')
