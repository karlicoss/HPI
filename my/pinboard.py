"""
[[https://pinboard.in][Pinboard]] bookmarks
"""
REQUIRES = [
    'git+https://github.com/karlicoss/pinbexport',
]

from my.config import pinboard as config


import pinbexport.dal as pinbexport

Bookmark = pinbexport.Bookmark


# yep; clearly looks that the purpose of my. package is to wire files to DAL implicitly; otherwise it's just passtrhough.
def dal() -> pinbexport.DAL:
    from .core import get_files
    inputs = get_files(config.export_dir) # todo rename to export_path
    model = pinbexport.DAL(inputs)
    return model


from typing import Iterable
def bookmarks() -> Iterable[pinbexport.Bookmark]:
    return dal().bookmarks()
