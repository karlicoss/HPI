"""
[[https://pinboard.in][Pinboard]] bookmarks
"""

REQUIRES = [
    'pinbexport @ git+https://github.com/karlicoss/pinbexport',
]

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

import pinbexport.dal as pinbexport

from my.core import Paths, Res, get_files, warnings


class config:
    @property
    def export_path(self) -> Paths:
        """Paths or globs pointing to Pinboard exports."""
        path = getattr(self, 'export_dir', None)
        if path is None:
            raise AttributeError('my.config.pinboard.export_path is not configured', name='export_path', obj=self)
        warnings.high('my.config.pinboard.export_dir is deprecated; rename it to my.config.pinboard.export_path')
        return cast(Paths, path)


def make_config() -> config:
    from my.config import pinboard as user_config

    class combined_config(user_config, config):
        pass

    return combined_config()


# TODO not sure if should keep this import here?
Bookmark = pinbexport.Bookmark


def inputs() -> Sequence[Path]:
    cfg = make_config()
    return get_files(cfg.export_path)


# yep; clearly looks that the purpose of my. package is to wire files to DAL implicitly; otherwise it's just passtrhough.
def dal() -> pinbexport.DAL:
    return pinbexport.DAL(inputs())


def bookmarks() -> Iterator[Res[pinbexport.Bookmark]]:
    return dal().bookmarks()
