from functools import lru_cache
from pathlib import Path

from mycfg.repos.pinbexport import model as pinbexport
from mycfg import paths

# TODO would be nice to make interfaces available for mypy...
Bookmark = pinbexport.Bookmark

def get_model():
    export_dir = Path(paths.pinbexport.export_dir)
    sources = list(sorted(export_dir.glob('*.json')))
    model = pinbexport.Model(sources)
    return model


def get_bookmarks():
    return get_model().bookmarks()
