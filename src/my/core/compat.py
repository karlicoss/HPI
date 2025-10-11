'''
Contains backwards compatibility helpers for different python versions.
If something is relevant to HPI itself, please put it in .hpi_compat instead
'''

from __future__ import annotations

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

    # keeping for runtime backwards compatibility (added in 3.9)
    @deprecated('use .removeprefix method on string directly instead')
    def removeprefix(text: str, prefix: str) -> str:
        return text.removeprefix(prefix)

    @deprecated('use .removesuffix method on string directly instead')
    def removesuffix(text: str, suffix: str) -> str:
        return text.removesuffix(suffix)

    ## used to have compat function before 3.8 for these, keeping for runtime back compatibility
    from bisect import bisect_left
    from functools import cached_property
    from types import NoneType

    ##
    ## used to have compat function before 3.9 for these, keeping for runtime back compatibility
    from typing import Literal, ParamSpec, Protocol, TypeAlias, TypedDict

    _KwOnlyType = TypedDict("_KwOnlyType", {"kw_only": Literal[True]})  # noqa: UP013
    KW_ONLY: _KwOnlyType = {"kw_only": True}
    ##

    ## old compat for python <3.12
    from datetime import datetime

    fromisoformat = datetime.fromisoformat

    from typing import Never, assert_never, assert_type

    add_note = BaseException.add_note
    ##
