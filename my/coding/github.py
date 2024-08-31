from typing import TYPE_CHECKING

from my.core import warnings

warnings.high('my.coding.github is deprecated! Please use my.github.all instead!')
# todo why aren't DeprecationWarning shown by default??

if not TYPE_CHECKING:
    from ..github.all import events, get_events  # noqa: F401

    # todo deprecate properly
    iter_events = events
