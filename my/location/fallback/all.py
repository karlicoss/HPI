# TODO: add config here which passes kwargs to estimate_from (under_accuracy)
# overwritable by passing the kwarg name here to the top-level estimate_location

from __future__ import annotations

from collections.abc import Iterator

from my.core.source import import_source
from my.location.fallback.common import (
    DateExact,
    FallbackLocation,
    LocationEstimator,
    estimate_from,
)


def fallback_locations() -> Iterator[FallbackLocation]:
    # can comment/uncomment sources here to enable/disable them
    yield from _ip_fallback_locations()


def fallback_estimators() -> Iterator[LocationEstimator]:
    # can comment/uncomment estimators here to enable/disable them
    # the order of the estimators determines priority if location accuries are equal/unavailable
    yield _ip_estimate
    yield _home_estimate


def estimate_location(dt: DateExact, *, first_match: bool=False, under_accuracy: int | None = None) -> FallbackLocation:
    loc = estimate_from(dt, estimators=list(fallback_estimators()), first_match=first_match, under_accuracy=under_accuracy)
    # should never happen if the user has home configured
    if loc is None:
        raise ValueError("Could not estimate location")
    return loc


@import_source(module_name="my.location.fallback.via_home")
def _home_estimate(dt: DateExact) -> Iterator[FallbackLocation]:
    from my.location.fallback.via_home import estimate_location as via_home_estimate

    yield from via_home_estimate(dt)


@import_source(module_name="my.location.fallback.via_ip")
def _ip_estimate(dt: DateExact) -> Iterator[FallbackLocation]:
    from my.location.fallback.via_ip import estimate_location as via_ip_estimate

    yield from via_ip_estimate(dt)


@import_source(module_name="my.location.fallback.via_ip")
def _ip_fallback_locations() -> Iterator[FallbackLocation]:
    from my.location.fallback.via_ip import fallback_locations as via_ip_fallback

    yield from via_ip_fallback()
