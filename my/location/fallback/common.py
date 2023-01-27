from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

from ..common import Location


@dataclass
class FallbackLocation:
    lat: float
    lon: float
    dt: datetime
    duration: float  # time in seconds for how long this is valid
    accuracy: Optional[float] = None
    elevation: Optional[float] = None
    datasource: Optional[str] = None  # which module provided this, useful for debugging

    def to_location(self, end: bool = False) -> Location:
        '''
        by default the start date is used for the location
        If end is True, the start date + duration is used
        '''
        dt: datetime = self.dt
        if end:
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
        lat: float,
        lon: float,
        dt: datetime,
        end_dt: datetime,
        accuracy: Optional[float] = None,
        elevation: Optional[float] = None,
        datasource: Optional[str] = None,
    ) -> 'FallbackLocation':
        '''
        Create FallbackLocation from a start date and an end date
        '''
        if end_dt < dt:
            raise ValueError('end_date must be after dt')
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


# TODO: create estimate location which uses other fallback_locations to estimate a location
