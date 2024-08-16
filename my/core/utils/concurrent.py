import sys
from concurrent.futures import Executor, Future
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

from ..compat import ParamSpec

_P = ParamSpec('_P')
_T = TypeVar('_T')


# https://stackoverflow.com/a/10436851/706389
class DummyExecutor(Executor):
    """
    This is useful if you're already using Executor for parallelising,
     but also want to provide an option to run the code serially (e.g. for debugging)
    """

    def __init__(self, max_workers: Optional[int] = 1) -> None:
        self._shutdown = False
        self._max_workers = max_workers

    if TYPE_CHECKING:
        if sys.version_info[:2] <= (3, 8):
            # 3.8 doesn't support ParamSpec as Callable arg :(
            # and any attempt to type results in incompatible supertype.. so whatever
            def submit(self, fn, *args, **kwargs): ...

        else:

            def submit(self, fn: Callable[_P, _T], /, *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]: ...

    else:

        def submit(self, fn, *args, **kwargs):
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            f: Future[Any] = Future()
            try:
                result = fn(*args, **kwargs)
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                f.set_exception(e)
            else:
                f.set_result(result)

            return f

    def shutdown(self, wait: bool = True, **kwargs) -> None:
        self._shutdown = True
