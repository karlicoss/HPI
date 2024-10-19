from __future__ import annotations

from concurrent.futures import Executor, Future
from typing import Any, Callable, TypeVar

from ..compat import ParamSpec

_P = ParamSpec('_P')
_T = TypeVar('_T')


# https://stackoverflow.com/a/10436851/706389
class DummyExecutor(Executor):
    """
    This is useful if you're already using Executor for parallelising,
     but also want to provide an option to run the code serially (e.g. for debugging)
    """

    def __init__(self, max_workers: int | None = 1) -> None:
        self._shutdown = False
        self._max_workers = max_workers

    def submit(self, fn: Callable[_P, _T], /, *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
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

    def shutdown(self, wait: bool = True, **kwargs) -> None:  # noqa: FBT001,FBT002,ARG002
        self._shutdown = True
