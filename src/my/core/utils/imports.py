from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


# TODO only used in tests? not sure if useful at all.
def import_file(p: Path | str, name: str | None = None) -> ModuleType:
    p = Path(p)
    if name is None:
        name = p.stem
    spec = importlib.util.spec_from_file_location(name, p)
    assert spec is not None, f"Fatal error; Could not create module spec from {name} {p}"
    foo = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(foo)
    return foo


def import_from(path: Path | str, name: str) -> ModuleType:
    path = str(path)
    sys.path.append(path)
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(path)


def import_dir(path: Path | str, extra: str = '') -> ModuleType:
    p = Path(path)
    if p.parts[0] == '~':
        p = p.expanduser()  # TODO eh. not sure about this..
    return import_from(p.parent, p.name + extra)
