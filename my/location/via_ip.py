REQUIRES = ["git+https://github.com/seanbreckenridge/ipgeocache"]

from .fallback.via_ip import *

from my.core.warnings import high

high("my.location.via_ip is deprecated, use my.location.fallback.via_ip instead")
