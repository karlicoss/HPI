# I think 'compat' should be for python-specific compat stuff, whereas this for HPI specific backwards compatibility
import inspect
import re
from typing import List

from my.core import warnings as W


def handle_legacy_import(
        parent_module_name: str,
        legacy_submodule_name: str,
        parent_module_path: List[str],
) -> bool:
    ###
    # this is to trick mypy into treating this as a proper namespace package
    # should only be used for backwards compatibility on packages that are convernted into namespace & all.py pattern
    # - https://www.python.org/dev/peps/pep-0382/#namespace-packages-today
    # - https://github.com/karlicoss/hpi_namespace_experiment
    # - discussion here https://memex.zulipchat.com/#narrow/stream/279601-hpi/topic/extending.20HPI/near/269946944
    from pkgutil import extend_path
    parent_module_path[:] = extend_path(parent_module_path, parent_module_name)
    # 'this' source tree ends up first in the pythonpath when we extend_path()
    # so we need to move 'this' source tree towards the end to make sure we prioritize overlays
    parent_module_path[:] = parent_module_path[1:] + parent_module_path[:1]
    ###

    # allow stuff like 'import my.module.submodule' and such
    imported_as_parent = False

    # allow stuff like 'from my.module import submodule'
    importing_submodule = False

    # some hacky traceback to inspect the current stack
    # to see if the user is using the old style of importing
    for f in inspect.stack():
        # seems that when a submodule is imported, at some point it'll call some internal import machinery
        # with 'parent' set to the parent module
        # if parent module is imported first (i.e. in case of deprecated usage), it won't be the case
        args = inspect.getargvalues(f.frame)
        if args.locals.get('parent') == parent_module_name:
            imported_as_parent = True

        # this we can only detect from the code I guess
        line = '\n'.join(f.code_context or [])
        if re.match(rf'from\s+{parent_module_name}\s+import\s+{legacy_submodule_name}', line):
            importing_submodule = True

    is_legacy_import = not (imported_as_parent or importing_submodule)
    if is_legacy_import:
        W.high(f'''\
importing {parent_module_name} is DEPRECATED! \
Instead, import from {parent_module_name}.{legacy_submodule_name} or {parent_module_name}.all \
See https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#allpy for more info.
''')
    return is_legacy_import
