from my.core import warnings

warnings.high("DEPRECATED! Use my.media.imdb instead.")

from my.core import __NOT_HPI_MODULE__  # noqa: F401  # isort: skip

from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    from .imdb import get_movies  # noqa: F401  # legacy import

# TODO extract items from org mode? perhaps not very high priority
