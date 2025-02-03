"""
Helpers to prevent depending on pytest in runtime
"""

import sys
import typing

under_pytest = 'pytest' in sys.modules

if typing.TYPE_CHECKING or under_pytest:
    import pytest

    parametrize = pytest.mark.parametrize
else:

    def parametrize(*_args, **_kwargs):
        def wrapper(f):
            return f

        return wrapper
