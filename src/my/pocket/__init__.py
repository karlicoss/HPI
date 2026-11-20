"""Deprecated import path for ``my.pocket.pockexport``."""

from my.core import __NOT_HPI_MODULE__  # noqa: F401
from my.core.hpi_compat import handle_legacy_import

# The module installer reads this declaration without importing the provider.
REQUIRES = [
    'pockexport @ git+https://github.com/karlicoss/pockexport',
]

handle_legacy_import(
    parent_module_name=__name__,
    legacy_submodule_name='pockexport',
    parent_module_path=__path__,
)
