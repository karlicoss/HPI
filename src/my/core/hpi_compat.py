"""
Contains various backwards compatibility/deprecation helpers relevant to HPI itself.
(as opposed to .compat module which implements compatibility between python versions)
"""

from __future__ import annotations

import os
import pkgutil
import sys
from collections.abc import MutableSequence, Sequence
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from . import warnings


def handle_legacy_import(
    *,
    parent_module_name: str,
    legacy_submodule_name: str,
    parent_module_path: MutableSequence[str],
) -> None:
    """Forward a package's old exports through module attribute hooks.

    Call this from the package's ``__init__.py`` without copying the provider's exports at runtime.
    Bare package imports are quiet; accessing a forwarded attribute emits the deprecation warning.
    """
    parent_module = sys.modules[parent_module_name]
    parent_file = parent_module.__file__
    assert parent_file is not None
    own_path = str(Path(parent_file).parent)

    # Keep the compatibility package extensible, with overlay providers taking precedence.
    # Partition by the package's own path so reloading it does not reverse that precedence.
    paths = pkgutil.extend_path(parent_module_path, parent_module_name)
    parent_module_path[:] = sorted(paths, key=lambda path: path == own_path)
    legacy_module_name = f'{parent_module_name}.{legacy_submodule_name}'

    def exported_names() -> Sequence[str]:
        provider = import_module(legacy_module_name)
        return getattr(provider, '__all__', [name for name in vars(provider) if not name.startswith('_')])

    def __getattr__(name: str) -> Any:
        if name == '__all__':
            return exported_names()

        # Leave import metadata and real submodules to Python's normal import machinery.
        # In particular, importing a sibling must not load the legacy provider's dependencies.
        if name.startswith('__') or '.' in name or find_spec(f'{parent_module_name}.{name}') is not None:
            raise AttributeError(f'module {parent_module_name!r} has no attribute {name!r}')
        if name not in exported_names():
            raise AttributeError(f'module {parent_module_name!r} has no attribute {name!r}')

        value = getattr(import_module(legacy_module_name), name)
        # Click sets this while completing commands; suppress warnings without caching the lookup.
        if '_HPI_COMPLETE' not in os.environ:
            warnings.high(
                f'''\
importing {parent_module_name} is DEPRECATED! \
Instead, import from {parent_module_name}.{legacy_submodule_name} or {parent_module_name}.all \
See https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#allpy for more info.
'''
            )
        return value

    def __dir__() -> list[str]:
        return sorted(set(vars(parent_module)) | set(exported_names()))

    vars(parent_module).update(__getattr__=__getattr__, __dir__=__dir__)
