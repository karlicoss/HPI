"""
Instapaper bookmarks, highlights and annotations
"""
from pathlib import Path
from typing import NamedTuple, Optional, List, Iterator

from .common import group_by_key, PathIsh, get_files


from my.config import instapaper as config
import my.config.repos.instapexport.dal as dal


def _get_files():
    return get_files(config.export_path, glob='*.json')


def get_dal() -> dal.DAL:
    return dal.DAL(_get_files())


# TODO meh, come up with better name...
class HighlightWithBm(NamedTuple):
    highlight: dal.Highlight
    bookmark: dal.Bookmark


def iter_highlights(**kwargs) -> Iterator[HighlightWithBm]:
    # meh...
    dl = get_dal()
    hls = dl.highlights()
    bms = dl.bookmarks()
    for _, h in hls.items():
        yield HighlightWithBm(highlight=h, bookmark=bms[h.bid])


# def get_highlights(**kwargs) -> List[Highlight]:
#     return list(iter_highlights(**kwargs))
def get_pages():
    return get_dal().pages()



def get_todos() -> Iterator[HighlightWithBm]:
    def is_todo(hl: HighlightWithBm):
        h = hl.highlight
        note = h.note or ''
        note = note.lstrip().lower()
        return note.startswith('todo')
    return filter(is_todo, iter_highlights())


def main():
    for h in get_todos():
        print(h)
