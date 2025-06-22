from my.core import warnings

# still used in Promnesia, maybe in dashboard?
warnings.high("DEPRECATED! Import my.config directly instead.")

from my.core import __NOT_HPI_MODULE__  # noqa: F401  # isort: skip

from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import my.config as config  # noqa: F401
