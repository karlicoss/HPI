from my.tests.common import skip_if_not_karlicoss as pytestmark  # isort: skip

from more_itertools import ilen


def test_events() -> None:
    from my.goodreads import events
    assert ilen(events()) > 20


def test_books() -> None:
    from my.goodreads import books
    assert ilen(books()) > 10
