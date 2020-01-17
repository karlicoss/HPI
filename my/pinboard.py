from .common import get_files

from mycfg.repos.pinbexport import dal as pinbexport
from mycfg import paths

# TODO would be nice to make interfaces available for mypy...
Bookmark = pinbexport.Bookmark


# yep; clearly looks that the purpose of my. package is to wire files to DAL implicitly; otherwise it's just passtrhough.
def dal():
    sources = get_files(paths.pinbexport.export_dir, glob='*.json')
    model = pinbexport.DAL(sources)
    return model


def bookmarks():
    return dal().bookmarks()
