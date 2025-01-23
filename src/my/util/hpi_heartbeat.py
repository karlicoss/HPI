"""
Just an helper module for testing HPI overlays
In particular the behaviour of import_original_module function

The idea of testing is that overlays extend this module, and add their own
items to items(), and the checker asserts all overlays have contributed.
"""

from my.core import __NOT_HPI_MODULE__  # isort: skip

import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

NOW = datetime.now()


@dataclass
class Item:
    dt: datetime
    message: str
    path: list[str]


def get_pkg_path() -> list[str]:
    pkg = sys.modules[__package__]
    return list(pkg.__path__)


# NOTE: since we're hacking path for my.util
# imports from my. should work as expected
# (even though my.config is in the private config)
from my.config import demo

assert demo.username == 'todo'

# however, this won't work while the module is imported
# from my.util import extra
# assert extra.message == 'EXTRA'
# but it will work when we actually call the function (see below)


def items() -> Iterator[Item]:
    from my.config import demo

    assert demo.username == 'todo'

    # here the import works as expected, since by the time the function is called,
    # all overlays were already processed and paths/sys.modules restored
    from my.util import extra  # type: ignore[attr-defined]

    assert extra.message == 'EXTRA'

    yield Item(dt=NOW, message='hpi main', path=get_pkg_path())
