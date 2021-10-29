"""
Decorator to gracefully handle importing a data source, or warning
and yielding nothing (or a default) when its not available
"""

from typing import Any, Iterator, TypeVar, Callable, Optional, Iterable, Any
from my.core.warnings import warn
from functools import wraps

# The factory function may produce something that has data
# similar to the shared model, but not exactly, so not
# making this a TypeVar, is just to make reading the
# type signature below a bit easier...
T = Any

# https://mypy.readthedocs.io/en/latest/generics.html?highlight=decorators#decorator-factories
FactoryF = TypeVar("FactoryF", bound=Callable[..., Iterator[T]])

_DEFUALT_ITR = ()


# tried to use decorator module but it really doesn't work well
# with types and kw-arguments... :/
def import_source(
    default: Iterable[T] = _DEFUALT_ITR,
    module_name: Optional[str] = None,
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
                res = factory_func(**kwargs)
                yield from res
            except ModuleNotFoundError:
                from . import core_config as CC
                suppressed_in_conf = False
                if module_name is not None and CC.config._is_module_active(module_name) is False:
                    suppressed_in_conf = True
                if not suppressed_in_conf:
                    if module_name is None:
                        warn(f"Module {factory_func.__qualname__} could not be imported, or isn't configured propertly")
                    else:
                        warn(f"""Module {module_name} ({factory_func.__qualname__}) could not be imported, or isn't configured propertly\nTo hide this message, add {module_name} to your core config disabled_classes, like:

class core:
    disabled_modules = [{repr(module_name)}]
""")
                yield from default
        return wrapper
    return decorator

