REQUIRES = ["git+https://github.com/purarue/ipgeocache"]

from my.core.warnings import high

from .fallback.via_ip import *

high("my.location.via_ip is deprecated, use my.location.fallback.via_ip instead")
