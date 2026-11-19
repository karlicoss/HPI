"""Deprecated import path for ``my.instapaper.instapexport``."""

from my.core import __NOT_HPI_MODULE__  # noqa: F401
from my.core.hpi_compat import handle_legacy_import

# The module installer reads this declaration without importing the provider.
REQUIRES = [
    'instapexport @ git+https://github.com/karlicoss/instapexport',
]

handle_legacy_import(
    parent_module_name=__name__,
    legacy_submodule_name='instapexport',
    parent_module_path=__path__,
)
