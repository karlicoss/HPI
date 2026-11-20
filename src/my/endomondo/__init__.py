"""Deprecated import path for ``my.endomondo.endoexport``."""

from my.core import __NOT_HPI_MODULE__  # noqa: F401
from my.core.hpi_compat import handle_legacy_import

# The module installer reads this declaration without importing the provider.
REQUIRES = [
    'endoexport[dal] @ git+https://github.com/karlicoss/endoexport',
]

handle_legacy_import(
    parent_module_name=__name__,
    legacy_submodule_name='endoexport',
    parent_module_path=__path__,
)
