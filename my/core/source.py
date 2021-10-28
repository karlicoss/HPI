from typing import Any, Iterator, TypeVar, Callable, Optional, Iterable
from my.core.warnings import warn

T = TypeVar("T")

# this is probably more generic and results in less code, but is not mypy-friendly
def import_source(factory: Callable[[], Any], default: Any) -> Any:
    try:
        res = factory()
        return res
    except ModuleNotFoundError: # presumable means the user hasn't installed the module
        warn(f"Module {factory.__qualname__} could not be imported, or isn't configured propertly")
        return default


# For an example of this, see the reddit.all file
def import_source_iter(factory: Callable[[], Iterator[T]], default: Optional[Iterable[T]] = None) -> Iterator[T]:
    if default is None:
        default = []
    try:
        res = factory()
        yield from res
    except ModuleNotFoundError: # presumable means the user hasn't installed the module
        warn(f"Module {factory.__qualname__} could not be imported, or isn't configured propertly")
        yield from default

