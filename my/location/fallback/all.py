# TODO: add config here which passes kwargs to estimate_from (under_accuracy)
# overwritable by passing the kwarg name here to the top-level estimate_location

from typing import Union
from datetime import datetime

from my.location.fallback.common import estimate_from, FallbackLocation

def estimate_location(dt: Union[datetime, float, int]) -> FallbackLocation:
    from my.location.fallback.via_home import estimate_location as via_home

    loc = estimate_from(
         dt,
         estimators=(via_home,)
    )
    if loc is None:
        raise ValueError("Could not estimate location")
    return loc

