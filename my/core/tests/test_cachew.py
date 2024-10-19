from __future__ import annotations

from .common import skip_if_uses_optional_deps as pytestmark

# TODO ugh, this is very messy.. need to sort out config overriding here


def test_cachew() -> None:
    from cachew import settings

    settings.ENABLE = True  # by default it's off in tests (see conftest.py)

    from my.core.cachew import mcachew

    called = 0

    # TODO ugh. need doublewrap or something to avoid having to pass parens
    @mcachew()
    def cf() -> list[int]:
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

    settings.ENABLE = True  # by default it's off in tests (see conftest.py)

    from my.core.cachew import cache_dir, mcachew
    from my.core.core_config import _reset_config as reset

    with reset() as cc:
        cc.cache_dir = None
        called = 0

        @mcachew(cache_path=cache_dir() / 'ctest')
        def cf() -> list[int]:
            nonlocal called
            called += 1
            return [called, called, called]

        assert list(cf()) == [1, 1, 1]
        assert list(cf()) == [2, 2, 2]
