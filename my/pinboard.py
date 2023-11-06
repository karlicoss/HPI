"""
[[https://pinboard.in][Pinboard]] bookmarks
"""
REQUIRES = [
    'git+https://github.com/karlicoss/pinbexport',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from my.core import get_files, Paths, Res
import my.config

import pinbexport.dal as pinbexport


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
