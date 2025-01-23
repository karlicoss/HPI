import my.config as config

from .core import __NOT_HPI_MODULE__
from .core import warnings as W

# still used in Promnesia, maybe in dashboard?
W.high("DEPRECATED! Please import my.config directly instead.")
