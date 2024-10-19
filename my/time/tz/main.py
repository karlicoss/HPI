'''
Timezone data provider, used to localize timezone-unaware timestamps for other modules
'''

from datetime import datetime

from my.core import datetime_aware


# todo hmm, kwargs isn't mypy friendly.. but specifying types would require duplicating default args. uhoh
def localize(dt: datetime, **kwargs) -> datetime_aware:
    # todo document patterns for combining multiple data sources
    # e.g. see https://github.com/karlicoss/HPI/issues/89#issuecomment-716495136
    from . import via_location as L
    from .common import localize_with_policy
    return localize_with_policy(L.localize, dt, **kwargs)
