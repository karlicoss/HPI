from my.core import warnings

warnings.high("DEPRECATED! Use my.hackernews.materialistic instead.")

from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    from .hackernews.materialistic import *
