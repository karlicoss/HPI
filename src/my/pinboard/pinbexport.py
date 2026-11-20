"""
[[https://pinboard.in][Pinboard]] bookmarks

Reads JSON exports from [[https://github.com/karlicoss/pinbexport][pinbexport]].
"""

REQUIRES = [
    'pinbexport @ git+https://github.com/karlicoss/pinbexport',
]

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

from pinbexport import dal as pinbexport_dal

from my.core import Paths, Res, get_files, warnings


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to Pinboard exports."""
        raise NotImplementedError


class _FlatConfig(Config):
    @property
    def export_path(self) -> Paths:
        """Fall back to export_dir when the user's flat config has no export_path."""
        path = getattr(self, 'export_dir', None)
        if path is None:
            raise AttributeError(
                'my.config.pinboard.pinbexport.export_path is not configured', name='export_path', obj=self
            )
        return cast(Paths, path)


def make_config() -> Config:
    from my.config import pinboard as user_config

    if hasattr(user_config, 'pinbexport'):

        class combined_config(user_config.pinbexport, Config):
            pass

        return combined_config()

    warnings.high('The flat Pinboard config is deprecated. Use my.config.pinboard.pinbexport.export_path instead.')

    class flat_config(user_config, _FlatConfig):
        pass

    return flat_config()


DAL = pinbexport_dal.DAL
Bookmark = pinbexport_dal.Bookmark


def inputs() -> Sequence[Path]:
    cfg = make_config()
    return get_files(cfg.export_path)


def dal() -> DAL:
    return DAL(inputs())


def bookmarks() -> Iterator[Res[Bookmark]]:
    return dal().bookmarks()
