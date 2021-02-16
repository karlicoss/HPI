'''
Some backwards compatibility stuff/deprecation helpers
'''
from types import ModuleType

from . import warnings
from .common import LazyLogger


logger = LazyLogger('my.core.compat')


def pre_pip_dal_handler(
        name: str,
        e: ModuleNotFoundError,
        cfg,
        requires=[],
) -> ModuleType:
    '''
    https://github.com/karlicoss/HPI/issues/79
    '''
    if e.name != name:
        # the module itself was imported, so the problem is with some dependencies
        raise e
    try:
        dal = _get_dal(cfg, name)
        warnings.high(f'''
Specifying modules' dependencies in the config or in my/config/repos is deprecated!
Please install {' '.join(requires)} as PIP packages (see the corresponding README instructions).
'''.strip(), stacklevel=2)
    except ModuleNotFoundError as ee:
        dal = None

    if dal is None:
        # probably means there was nothing in the old config in the first place
        # so we should raise the original exception
        raise e
    return dal


def _get_dal(cfg, module_name: str):
    mpath = getattr(cfg, module_name, None)
    if mpath is not None:
        from .common import import_dir
        return import_dir(mpath, '.dal')
    else:
        from importlib import import_module
        return import_module(f'my.config.repos.{module_name}.dal')


import sys
from typing import TYPE_CHECKING

if sys.version_info[:2] >= (3, 8):
    from typing import Literal
else:
    if TYPE_CHECKING:
        from typing_extensions import Literal
    else:
        from typing import Union
        # erm.. I guess as long as it's not crashing, whatever...
        Literal = Union


import os
windows = os.name == 'nt'
