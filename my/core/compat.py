'''
Contains backwards compatibility helpers for different python versions.
If something is relevant to HPI itself, please put it in .hpi_compat instead
'''

import sys
from typing import TYPE_CHECKING

if sys.version_info[:2] >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated


# keeping just for backwards compatibility, used to have compat implementation for 3.6
if not TYPE_CHECKING:
    import sqlite3

    @deprecated('use .backup method on sqlite3.Connection directly instead')
    def sqlite_backup(*, source: sqlite3.Connection, dest: sqlite3.Connection, **kwargs) -> None:
        # TODO warn here?
        source.backup(dest, **kwargs)


# can remove after python3.9 (although need to keep the method itself for bwd compat)
def removeprefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


## used to have compat function before 3.8 for these, keeping for runtime back compatibility
if not TYPE_CHECKING:
    from functools import cached_property
    from typing import Literal, Protocol, TypedDict
else:
    from typing_extensions import Literal, Protocol, TypedDict
##


if sys.version_info[:2] >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


# bisect_left doesn't have a 'key' parameter (which we use)
# till python3.10
if sys.version_info[:2] <= (3, 9):
    from typing import Any, Callable, List, Optional, TypeVar

    X = TypeVar('X')

    # copied from python src
    # fmt: off
    def bisect_left(a: List[Any], x: Any, lo: int=0, hi: Optional[int]=None, *, key: Optional[Callable[..., Any]]=None) -> int:
        if lo < 0:
            raise ValueError('lo must be non-negative')
        if hi is None:
            hi = len(a)
        # Note, the comparison uses "<" to match the
        # __lt__() logic in list.sort() and in heapq.
        if key is None:
            while lo < hi:
                mid = (lo + hi) // 2
                if a[mid] < x:
                    lo = mid + 1
                else:
                    hi = mid
        else:
            while lo < hi:
                mid = (lo + hi) // 2
                if key(a[mid]) < x:
                    lo = mid + 1
                else:
                    hi = mid
        return lo
    # fmt: on

else:
    from bisect import bisect_left


from datetime import datetime

if sys.version_info[:2] >= (3, 11):
    fromisoformat = datetime.fromisoformat
else:
    # fromisoformat didn't support Z as "utc" before 3.11
    # https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat

    def fromisoformat(date_string: str) -> datetime:
        if date_string.endswith('Z'):
            date_string = date_string[:-1] + '+00:00'
        return datetime.fromisoformat(date_string)


def test_fromisoformat() -> None:
    from datetime import timezone

    # fmt: off
    # feedbin has this format
    assert fromisoformat('2020-05-01T10:32:02.925961Z') == datetime(
        2020, 5, 1, 10, 32, 2, 925961, timezone.utc,
    )

    # polar has this format
    assert fromisoformat('2018-11-28T22:04:01.304Z') == datetime(
        2018, 11, 28, 22, 4, 1, 304000, timezone.utc,
    )

    # stackexchange, runnerup has this format
    assert fromisoformat('2020-11-30T00:53:12Z') == datetime(
        2020, 11, 30, 0, 53, 12, 0, timezone.utc,
    )
    # fmt: on

    # arbtt has this format (sometimes less/more than 6 digits in milliseconds)
    # TODO doesn't work atm, not sure if really should be supported...
    # maybe should have flags for weird formats?
    # assert isoparse('2017-07-18T18:59:38.21731Z') == datetime(
    #     2017, 7, 18, 18, 59, 38, 217310, timezone.utc,
    # )


if sys.version_info[:2] >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)


if sys.version_info[:2] >= (3, 11):
    from typing import Never, assert_never, assert_type
else:
    from typing_extensions import Never, assert_never, assert_type
