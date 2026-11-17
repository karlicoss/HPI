# The legacy-import detector misidentifies relative from-imports; import the concrete provider directly.
import my.jawbone.api as jawbone

from ... import emfit
from .common import Combine

_combined = Combine(
    [
        jawbone,
        emfit,
    ]
)

dataframe = _combined.dataframe
stats = _combined.stats
