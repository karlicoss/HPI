"""
[[https://pinboard.in][Pinboard]] bookmarks
"""
from .common import get_files

from my.config.repos.pinbexport import dal as pinbexport
from my.config import pinboard as config

# TODO would be nice to make interfaces available for mypy...
Bookmark = pinbexport.Bookmark


# yep; clearly looks that the purpose of my. package is to wire files to DAL implicitly; otherwise it's just passtrhough.
def dal():
    sources = get_files(config.export_dir, glob='*.json')
    model = pinbexport.DAL(sources)
    return model


def bookmarks():
    return dal().bookmarks()
