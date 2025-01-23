"""
[[https://pinboard.in][Pinboard]] bookmarks
"""
REQUIRES = [
    'git+https://github.com/karlicoss/pinbexport',
]

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pinbexport.dal as pinbexport

from my.core import Paths, Res, get_files

import my.config  # isort: skip


@dataclass
class config(my.config.pinboard):  # TODO rename to pinboard.pinbexport?
    # TODO rename to export_path?
    export_dir: Paths


# TODO not sure if should keep this import here?
Bookmark = pinbexport.Bookmark


def inputs() -> Sequence[Path]:
    return get_files(config.export_dir)


# yep; clearly looks that the purpose of my. package is to wire files to DAL implicitly; otherwise it's just passtrhough.
def dal() -> pinbexport.DAL:
    return pinbexport.DAL(inputs())


def bookmarks() -> Iterator[Res[pinbexport.Bookmark]]:
    return dal().bookmarks()
