from pathlib import Path

import pytest


def test_legacy_pathish_imports() -> None:
    """Old annotations and isinstance checks keep working, with warnings at the importing code."""
    with pytest.warns(UserWarning, match=r'my\.core\.PathIsh is deprecated; use pathlib.Path \| str') as core_warnings:
        from my.core import PathIsh  # type: ignore[attr-defined]  # ty: ignore[missing-module-member]

    with pytest.warns(
        UserWarning, match=r'my\.core\.common\.PathIsh is deprecated; use pathlib.Path \| str'
    ) as common_warnings:
        from my.core.common import PathIsh as CommonPathIsh  # type: ignore[attr-defined]  # ty: ignore[missing-module-member]

    assert PathIsh == CommonPathIsh == Path | str
    assert isinstance(Path('export.json'), PathIsh)
    assert isinstance('export.json', CommonPathIsh)
    assert not isinstance(['export.json'], PathIsh)
    assert all(warning.filename == __file__ for warning in [*core_warnings, *common_warnings])


def test_legacy_mcachew_call() -> None:
    """Using the legacy decorator warns at the caller and still produces a working decorated function."""
    from my.core.common import mcachew  # type: ignore[attr-defined]  # ty: ignore[missing-module-member]

    with pytest.warns(DeprecationWarning, match=r'use my\.core\.cachew\.mcachew instead') as caught:

        @mcachew(cache_path=None)
        def values() -> list[int]:
            return [1, 2]

    assert list(values()) == [1, 2]
    assert caught.pop(DeprecationWarning).filename == __file__
