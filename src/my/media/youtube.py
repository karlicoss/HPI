from my.core import __NOT_HPI_MODULE__  # isort: skip

from typing import TYPE_CHECKING

from my.core.warnings import high

high("DEPRECATED! Please use my.youtube.takeout instead.")

if not TYPE_CHECKING:
    from my.youtube.takeout import *
