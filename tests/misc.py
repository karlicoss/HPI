from typing import Iterable, List
import warnings
from my.core import warn_if_empty


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
    from my.core.common import _warn_iterable
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
        assert x1 is i1 # should be unchanged!
        assert len(w) == 0

        assert list(x2) == [1, 2, 3]
        assert len(w) == 0


def test_cachew() -> None:
    from cachew import settings
    settings.ENABLE = True # by default it's off in tests (see conftest.py)

    from my.core.cachew import cache_dir
    from my.core.common import mcachew

    called = 0
    # FIXME ugh. need doublewrap or something
    @mcachew()
    def cf() -> List[int]:
        nonlocal called
        called += 1
        return [1, 2, 3]

    list(cf())
    cc = called
    # todo ugh. how to clean cache?
    # assert called == 1 # precondition, to avoid turdes from previous tests

    assert list(cf()) == [1, 2, 3]
    assert called == cc


def test_cachew_dir_none() -> None:
    from cachew import settings
    settings.ENABLE = True # by default it's off in tests (see conftest.py)

    from my.core.cachew import cache_dir
    from my.core.common import mcachew
    from my.core.core_config import _reset_config as reset
    with reset() as cc:
        cc.cache_dir = None
        called = 0
        @mcachew(cache_path=cache_dir() / 'ctest')
        def cf() -> List[int]:
            nonlocal called
            called += 1
            return [called, called, called]
        assert list(cf()) == [1, 1, 1]
        assert list(cf()) == [2, 2, 2]
