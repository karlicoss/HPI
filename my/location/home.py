from my.core.warnings import high

from .fallback.via_home import *

high(
    "my.location.home is deprecated, use my.location.fallback.via_home instead, or estimate locations using the higher-level my.location.fallback.all.estimate_location"
)
