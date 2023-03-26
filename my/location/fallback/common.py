from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable, Sequence, Iterator, List, Union
from datetime import datetime, timedelta, timezone

from ..common import LocationProtocol, Location
DateExact = Union[datetime, float, int]  # float/int as epoch timestamps

Second = float

@dataclass
class FallbackLocation(LocationProtocol):
    lat: float
    lon: float
    dt: datetime
    duration: Optional[Second] = None
    accuracy: Optional[float] = None
    elevation: Optional[float] = None
    datasource: Optional[str] = None  # which module provided this, useful for debugging

    def to_location(self, end: bool = False) -> Location:
        '''
        by default the start date is used for the location
        If end is True, the start date + duration is used
        '''
        dt: datetime = self.dt
        if end and self.duration is not None:
            dt += timedelta(self.duration)
        return Location(
            lat=self.lat,
            lon=self.lon,
            dt=dt,
            accuracy=self.accuracy,
            elevation=self.elevation,
            datasource=self.datasource,
        )

    @classmethod
    def from_end_date(
        cls,
        *,
        lat: float,
        lon: float,
        dt: datetime,
        end_dt: datetime,
        accuracy: Optional[float] = None,
        elevation: Optional[float] = None,
        datasource: Optional[str] = None,
    ) -> FallbackLocation:
        '''
        Create FallbackLocation from a start date and an end date
        '''
        if end_dt < dt:
            raise ValueError("end_date must be after dt")
        duration = (end_dt - dt).total_seconds()
        return cls(
            lat=lat,
            lon=lon,
            dt=dt,
            duration=duration,
            accuracy=accuracy,
            elevation=elevation,
            datasource=datasource,
        )


# a location estimator can return multiple fallbacks, in case there are
# differing accuracies/to allow for possible matches to be computed
# iteratively
LocationEstimator = Callable[[DateExact], Iterator[FallbackLocation]]
LocationEstimators = Sequence[LocationEstimator]

# helper function, instead of dealing with datetimes while comparing, just use epoch timestamps
def _datetime_timestamp(dt: DateExact) -> float:
    if isinstance(dt, datetime):
        try:
            return dt.timestamp()
        except ValueError:
            # https://github.com/python/cpython/issues/75395
            return dt.replace(tzinfo=timezone.utc).timestamp()
    return float(dt)

def _iter_estimate_from(
    dt: DateExact,
    estimators: LocationEstimators,
) -> Iterator[FallbackLocation]:
    for est in estimators:
        yield from est(dt)


def estimate_from(
    dt: DateExact,
    estimators: LocationEstimators,
    *,
    first_match: bool = False,
    under_accuracy: Optional[int] = None,
) -> Optional[FallbackLocation]:
    '''
    first_match: if True, return the first location found
    under_accuracy: if set, only return locations with accuracy under this value
    '''
    found: List[FallbackLocation] = []
    for loc in _iter_estimate_from(dt, estimators):
        if under_accuracy is not None and loc.accuracy is not None and loc.accuracy > under_accuracy:
            continue
        if first_match:
            return loc
        found.append(loc)

    if not found:
        return None

    # if all items have accuracy, return the one with the lowest accuracy
    # otherwise, we should prefer the order that the estimators are passed in as
    if all(loc.accuracy is not None for loc in found):
        # return the location with the lowest accuracy
        return min(found, key=lambda loc: loc.accuracy)  # type: ignore[return-value, arg-type]
    else:
        # return the first location
        return found[0]
