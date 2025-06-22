from my.core import warnings

warnings.high("DEPRECATED! Use my.core.error instead.")

from my.core import __NOT_HPI_MODULE__  # noqa: F401  # isort: skip


from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    from my.core.error import *
