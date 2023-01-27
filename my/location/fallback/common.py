from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

from ..common import Location


@dataclass
class FallbackLocation:
    lat: float
    lon: float
    dt: datetime
    duration: int  # time in seconds for how long this is valid
    accuracy: Optional[float] = None
    elevation: Optional[float] = None
    datasource: Optional[str] = None  # which module provided this, useful for debugging

    def to_location(self, end: bool = False) -> Location:
        """
        by default the start date is used for the location
        If end is True, the start date + duration is used
        """
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
