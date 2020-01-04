"""
Uses instapaper API data export JSON file.

Set via
- ~configure~ method
- or in ~mycfg.instpaper.export_path~
"""
from datetime import datetime
import json
from pathlib import Path
from typing import NamedTuple, Optional, List, Dict, Iterator, Tuple
from collections import OrderedDict

import pytz

from .common import group_by_key, PathIsh, get_files


# TODO need to make configurable?
# TODO wonder if could autodetect from promnesia somehow..
# tbh, seems like venvs would be suited well for that..
import mycfg.repos.instapexport.dal as dal


_export_path: Optional[Path] = None
def configure(*, export_path: Optional[PathIsh]=None) -> None:
    if export_path is not None:
        global _export_path
        _export_path = Path(export_path)


def _get_files():
    export_path = _export_path
    if export_path is None:
        # fallback to mycfg
        from mycfg import paths
        export_path = paths.instapaper.export_path
    return get_files(export_path, glob='*.json')


def get_dal() -> dal.DAL:
    return dal.DAL(_get_files())


def iter_highlights(**kwargs) -> Iterator[dal.Highlight]:
    return iter(get_dal().highlights().values())


# def get_highlights(**kwargs) -> List[Highlight]:
#     return list(iter_highlights(**kwargs))
def get_pages():
    return get_dal().pages()


def get_todos() -> List[dal.Highlight]:
    def is_todo(h):
        note = h.note or ''
        note = note.lstrip().lower()
        return note.startswith('todo')
    return list(filter(is_todo, iter_highlights()))


def test_get_todos():
    for t in get_todos():
        print(t)


def main():
    for h in get_todos():
        print(h)
