from . import warnings

warnings.high(f"{__name__} is deprecated, please use dataset directly if you need or switch to my.core.sqlite")

from ._deprecated.dataset import *
