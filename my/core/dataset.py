from __future__ import annotations
from .common import assert_subpackage; assert_subpackage(__name__)

from .common import PathIsh
from .compat import Protocol
from .sqlite import sqlite_connect_immutable

## sadly dataset doesn't have any type definitions
from typing import Iterable, Iterator, Dict, Optional, Any
from contextlib import AbstractContextManager


# NOTE: may not be true in general, but will be in the vast majority of cases
row_type_T = Dict[str, Any]


class TableT(Iterable, Protocol):
    def find(self, *, order_by: Optional[str]=None) -> Iterator[row_type_T]: ...


class DatabaseT(AbstractContextManager['DatabaseT'], Protocol):
    def __getitem__(self, table: str) -> TableT: ...
##

# TODO wonder if also need to open without WAL.. test this on read-only directory/db file
def connect_readonly(db: PathIsh) -> DatabaseT:
    import dataset # type: ignore
    # see https://github.com/pudo/dataset/issues/136#issuecomment-128693122
    # todo not sure if mode=ro has any benefit, but it doesn't work on read-only filesystems
    # maybe it should autodetect readonly filesystems and apply this? not sure
    creator = lambda: sqlite_connect_immutable(db)
    return dataset.connect('sqlite:///', engine_kwargs={'creator': creator})
