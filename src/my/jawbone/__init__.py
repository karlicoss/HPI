"""Deprecated import path for ``my.jawbone.api``."""

from my.core import __NOT_HPI_MODULE__  # noqa: F401
from my.core.hpi_compat import handle_legacy_import

handle_legacy_import(
    parent_module_name=__name__,
    legacy_submodule_name='api',
    parent_module_path=__path__,
)
