"""
Helpers to prevent depending on pytest in runtime
"""

from .common import assert_subpackage; assert_subpackage(__name__)

import sys
import typing

under_pytest = 'pytest' in sys.modules

if typing.TYPE_CHECKING or under_pytest:
    import pytest

    parametrize = pytest.mark.parametrize
else:

    def parametrize(*args, **kwargs):
        def wrapper(f):
            return f

        return wrapper
