import ast
from pathlib import Path

import pytest

from my.core.compat import HPIDeprecationWarning


def test_deprecated_uses_hpi_category() -> None:
    """
    Every `deprecated()` in HPI must pass `category=HPIDeprecationWarning`.
    Python hides the default `DeprecationWarning` unless the deprecated call comes from `__main__`.
    """
    my_root = Path(__file__).parents[2]
    found = 0
    bare: list[str] = []
    for path in sorted(my_root.rglob('*.py')):
        # Parse bytes so the source encoding doesn't depend on the locale (e.g. cp1252 on Windows).
        for node in ast.walk(ast.parse(path.read_bytes())):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            else:
                continue
            if name != 'deprecated':
                continue
            found += 1
            category = next((kw.value for kw in node.keywords if kw.arg == 'category'), None)
            if not (isinstance(category, ast.Name) and category.id == HPIDeprecationWarning.__name__):
                bare.append(f'{path.relative_to(my_root.parent)}:{node.lineno}')
    assert found > 0
    assert bare == []


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

    with pytest.warns(HPIDeprecationWarning, match=r'use my\.core\.cachew\.mcachew instead') as caught:

        @mcachew(cache_path=None)
        def values() -> list[int]:
            return [1, 2]

    assert list(values()) == [1, 2]
    assert caught.pop(HPIDeprecationWarning).filename == __file__
