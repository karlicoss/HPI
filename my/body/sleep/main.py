from ... import jawbone
from ... import emfit

from .common import Combine
_combined = Combine([
    jawbone,
    emfit,
])

dataframe = _combined.dataframe
stats     = _combined.stats
