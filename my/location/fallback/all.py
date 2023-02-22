# TODO: add config here which passes kwargs to estimate_from (under_accuracy)
# overwritable by passing the kwarg name here to the top-level estimate_location

from typing import Iterator

from my.core.source import import_source
from my.location.fallback.common import estimate_from, FallbackLocation, DateExact

# note: the import_source returns an iterator
@import_source(module_name="my.location.fallback.via_home")
def _home_estimate(dt: DateExact) -> Iterator[FallbackLocation]:
    from my.location.fallback.via_home import estimate_location as via_home

    yield from via_home(dt)



def estimate_location(dt: DateExact) -> FallbackLocation:
    loc = estimate_from(
         dt,
         estimators=(_home_estimate,)
    )
    if loc is None:
        raise ValueError("Could not estimate location")
    return loc

