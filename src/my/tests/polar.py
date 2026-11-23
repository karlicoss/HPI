from pathlib import Path

import pytest

import my.config
from my import polar
from my.core.error import raise_exceptions
from my.tests.common import testdata


def test_polardocs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read the books and their page highlights from the pinned polardocs library."""

    class user_config:
        polar_dir = testdata() / 'polardocs'

    monkeypatch.setattr(my.config, 'polar', user_config, raising=False)
    books = {book.title: book for book in raise_exceptions(polar.get_entries())}
    assert {title: len(book.items) for title, book in books.items()} == {
        None: 3,
        're-frame: EffectfulHandlers': 75,
        're-frame: Interceptors': 9,
    }
    assert all(book.path.is_file() for book in books.values())
    assert any(
        h.selection == 'Events "happen" when they are dispatched.' and h.page == 1 and h.color == 'red'
        for h in books['re-frame: EffectfulHandlers'].items
    )


def test_missing_config_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(my.config, 'polar', raising=False)
    config = polar.make_config()
    assert config.polar_dir == Path.home() / '.polar'
    assert config.defensive is True
