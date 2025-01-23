"""
Unified Github data (merged from GDPR export and periodic API updates)
"""

from . import gdpr, ghexport
from .common import Results, merge_events


def events() -> Results:
    yield from merge_events(
        gdpr.events(),
        ghexport.events(),
    )


# todo hmm. not sure, maybe should be named sorted_events or something..
# also, not great that it's in all.py... think of a better way...
def get_events() -> Results:
    from ..core.error import sort_res_by
    return sort_res_by(events(), key=lambda e: e.dt)
