from ...emfit import emfitexport as emfit
from ...jawbone import api as jawbone
from .common import Combine

_combined = Combine(
    [
        jawbone,
        emfit,
    ]
)

dataframe = _combined.dataframe
stats = _combined.stats
