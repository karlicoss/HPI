from __future__ import annotations

import sys
import types
from typing import Any


# The idea behind this one is to support accessing "overlaid/shadowed" modules from namespace packages
# See usage examples here:
# - https://github.com/karlicoss/hpi-personal-overlay/blob/master/src/my/util/hpi_heartbeat.py
# - https://github.com/karlicoss/hpi-personal-overlay/blob/master/src/my/twitter/all.py
# Suppose you want to use my.twitter.talon, which isn't in the default all.py
# You could just copy all.py to your personal overlay, but that would mean duplicating
# all the code and possible upstream changes.
# Alternatively, you could import the "original" my.twitter.all module from "overlay" my.twitter.all
# _ORIG = import_original_module(__name__, __file__)
# this would magically take care of package import path etc,
# and should import the "original" my.twitter.all as _ORIG
# After that you can call its methods, extend etc.
def import_original_module(
    c__module__: str,
    c__file__: str,
    *,
    star: bool = False,
    globals: dict[str, Any] | None = None,  # noqa: A002
) -> types.ModuleType:
    """
    :param c__module__: __module__ of the callee.
    :param c__file__: __file__ of the callee
    :param start: if True, do 'import *' from the original module (into 'globals' dict, which needs to be set)
    :param globals: if star is True, this is the globals dict to update
    """
    if star:
        assert globals is not None, "globals must be set if star is True"

    module_to_restore = sys.modules[c__module__]

    # NOTE: we really wanna to hack the actual package of the module
    # rather than just top level my.
    # since that would be a bit less disruptive
    module_pkg = module_to_restore.__package__
    assert module_pkg is not None
    parent = sys.modules[module_pkg]

    my_path = parent.__path__._path  # type: ignore[attr-defined]
    my_path_orig = list(my_path)

    def fixup_path() -> None:
        for p in my_path_orig:
            starts = c__file__.startswith(p)
            if starts:
                my_path.remove(p)
        # should remove at least one item
        # sometimes it can be >1 when pytest is involved or some other path madness
        assert len(my_path) < len(my_path_orig), (my_path, my_path_orig, c__file__)

    try:
        # first, prepare module path to perform the import
        fixup_path()
        try:
            del sys.modules[c__module__]
            # NOTE: we're using __import__ instead of importlib.import_module
            # since it's closer to the actual normal import (e.g. imports subpackages etc properly )
            # fromlist=[None] forces it to return rightmost child
            # (otherwise would just return 'my' package)
            res = __import__(c__module__, fromlist=[None])  # type: ignore[list-item]
            if star:
                assert globals is not None
                globals.update({k: v for k, v in vars(res).items() if not k.startswith('_')})
            return res
        finally:
            sys.modules[c__module__] = module_to_restore
    finally:
        my_path[:] = my_path_orig
