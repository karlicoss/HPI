import sys
from typing import Any, Dict, Optional
import types


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
    module_name: str,
    file: str,
    *,
    star: bool = False,
    globals: Optional[Dict[str, Any]] = None,
) -> types.ModuleType:
    module_to_restore = sys.modules[module_name]

    # NOTE: we really wanna to hack the actual package of the module
    # rather than just top level my.
    # since that would be a bit less disruptive
    module_pkg = module_to_restore.__package__
    assert module_pkg is not None
    parent = sys.modules[module_pkg]

    my_path = parent.__path__._path  # type: ignore[attr-defined]
    my_path_orig = list(my_path)

    def fixup_path() -> None:
        for i, p in enumerate(my_path_orig):
            starts = file.startswith(p)
            if i == 0:
                # not sure about this.. but I guess it'll always be 0th element?
                assert starts, (my_path_orig, file)
            if starts:
                my_path.remove(p)
        # should remove exactly one item
        assert len(my_path) + 1 == len(my_path_orig), (my_path_orig, file)

    try:
        fixup_path()
        try:
            del sys.modules[module_name]
            # NOTE: we're using __import__ instead of importlib.import_module
            # since it's closer to the actual normal import (e.g. imports subpackages etc properly )
            # fromlist=[None] forces it to return rightmost child
            # (otherwise would just return 'my' package)
            res = __import__(module_name, fromlist=[None])  # type: ignore[list-item]
            if star:
                assert globals is not None
                globals.update({k: v for k, v in vars(res).items() if not k.startswith('_')})
            return res
        finally:
            sys.modules[module_name] = module_to_restore
    finally:
        my_path[:] = my_path_orig
