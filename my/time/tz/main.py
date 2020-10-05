'''
Timezone data provider
'''
from datetime import datetime

def localize(dt: datetime) -> datetime:
    # For now, it's user's reponsibility to check that it actually managed to localize
    from . import via_location as L
    return L.localize(dt)
