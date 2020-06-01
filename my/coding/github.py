import warnings

warnings.warn('my.coding.github is deprecated! Please use my.github.all instead!', DeprecationWarning)

from ..github.all import events, get_events

# todo deprecate properly
iter_events = events
