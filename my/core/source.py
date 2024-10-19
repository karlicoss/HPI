"""
Decorator to gracefully handle importing a data source, or warning
and yielding nothing (or a default) when its not available
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Iterator
from functools import wraps
from typing import Any, Callable, TypeVar

from .warnings import medium

# The factory function may produce something that has data
# similar to the shared model, but not exactly, so not
# making this a TypeVar, is just to make reading the
# type signature below a bit easier...
T = Any

# https://mypy.readthedocs.io/en/latest/generics.html?highlight=decorators#decorator-factories
FactoryF = TypeVar("FactoryF", bound=Callable[..., Iterator[T]])

_DEFAULT_ITR = ()


# tried to use decorator module but it really doesn't work well
# with types and kw-arguments... :/
def import_source(
    *,
    default: Iterable[T] = _DEFAULT_ITR,
    module_name: str | None = None,
    help_url: str | None = None,
) -> Callable[..., Callable[..., Iterator[T]]]:
    """
    doesn't really play well with types, but is used to catch
    ModuleNotFoundError's for when modules aren't installed in
    all.py files, so the types don't particularly matter

    this is meant to be used to wrap some function which imports
    and then yields an iterator of objects

    If the user doesn't have that module installed, it returns
    nothing and warns instead
    """

    def decorator(factory_func: FactoryF) -> Callable[..., Iterator[T]]:
        @wraps(factory_func)
        def wrapper(*args, **kwargs) -> Iterator[T]:
            try:
                res = factory_func(*args, **kwargs)
                yield from res
            except (ImportError, AttributeError) as err:
                from . import core_config as CC
                from .error import warn_my_config_import_error

                suppressed_in_conf = False
                if module_name is not None and CC.config._is_module_active(module_name) is False:
                    suppressed_in_conf = True
                if not suppressed_in_conf:
                    if module_name is None:
                        medium(f"Module {factory_func.__qualname__} could not be imported, or isn't configured properly")
                    else:
                        medium(f"Module {module_name} ({factory_func.__qualname__}) could not be imported, or isn't configured properly")
                        warnings.warn(f"""If you don't want to use this module, to hide this message, add '{module_name}' to your core config disabled_modules in your config, like:

class core:
    disabled_modules = [{module_name!r}]
""", stacklevel=1)
                    # try to check if this is a config error or based on dependencies not being installed
                    if isinstance(err, (ImportError, AttributeError)):
                        matched_config_err = warn_my_config_import_error(err, module_name=module_name, help_url=help_url)
                        # if we determined this wasn't a config error, and it was an attribute error
                        # it could be *any* attribute error -- we should raise this since its otherwise a fatal error
                        # from some code in the module failing
                        if not matched_config_err and isinstance(err, AttributeError):
                            raise err
                yield from default

        return wrapper

    return decorator
