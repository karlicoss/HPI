'''
Just a demo module for testing and documentation purposes
'''
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Protocol

from my.core import Json, PathIsh, Paths, get_files


class config(Protocol):
    data_path: Paths

    # this is to check required attribute handling
    username: str

    # this is to check optional attribute handling
    timezone: tzinfo = timezone.utc

    external: PathIsh | None = None

    @property
    def external_module(self):
        rpath = self.external
        if rpath is not None:
            from my.core.utils.imports import import_dir

            return import_dir(rpath)

        import my.config.repos.external as m  # type: ignore[import-not-found]

        return m


def make_config() -> config:
    from my.config import demo as user_config

    class combined_config(user_config, config): ...

    return combined_config()


@dataclass
class Item:
    '''
    Some completely arbitrary artificial stuff, just for testing
    '''

    username: str
    raw: Json
    dt: datetime


def inputs() -> Sequence[Path]:
    cfg = make_config()
    return get_files(cfg.data_path)


def items() -> Iterable[Item]:
    cfg = make_config()

    transform = (lambda i: i) if cfg.external is None else cfg.external_module.transform

    for f in inputs():
        dt = datetime.fromtimestamp(f.stat().st_mtime, tz=cfg.timezone)
        j = json.loads(f.read_text())
        for raw in j:
            yield Item(
                username=cfg.username,
                raw=transform(raw),
                dt=dt,
            )
