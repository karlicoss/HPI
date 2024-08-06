from typing import Iterable, List
import warnings

from ..common import (
    warn_if_empty,
    _warn_iterable,
)


def test_warn_if_empty() -> None:
    @warn_if_empty
    def nonempty() -> Iterable[str]:
        yield 'a'
        yield 'aba'

    @warn_if_empty
    def empty() -> List[int]:
        return []

    # should be rejected by mypy!
    # todo how to actually test it?
    # @warn_if_empty
    # def baad() -> float:
    #     return 0.00

    # reveal_type(nonempty)
    # reveal_type(empty)

    with warnings.catch_warnings(record=True) as w:
        assert list(nonempty()) == ['a', 'aba']
        assert len(w) == 0

        eee = empty()
        assert eee == []
        assert len(w) == 1


def test_warn_iterable() -> None:
    i1: List[str] = ['a', 'b']
    i2: Iterable[int] = iter([1, 2, 3])
    # reveal_type(i1)
    # reveal_type(i2)
    x1 = _warn_iterable(i1)
    x2 = _warn_iterable(i2)
    # vvvv this should be flagged by mypy
    # _warn_iterable(123)
    # reveal_type(x1)
    # reveal_type(x2)
    with warnings.catch_warnings(record=True) as w:
        assert x1 is i1  # should be unchanged!
        assert len(w) == 0

        assert list(x2) == [1, 2, 3]
        assert len(w) == 0
