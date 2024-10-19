from ... import emfit, jawbone
from .common import Combine

_combined = Combine([
    jawbone,
    emfit,
])

dataframe = _combined.dataframe
stats     = _combined.stats
