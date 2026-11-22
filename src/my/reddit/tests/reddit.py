import pytest
from more_itertools import consume

import my.reddit.all as my_reddit_all
import my.reddit.rexport as my_reddit_rexport
from my.core import __NOT_HPI_MODULE__, unwrap  # noqa: F401
from my.core.cachew import disabled_cachew
from my.core.cfg import tmp_config
from my.core.utils.itertools import ensure_unique
from my.tests.common import testdata


def test_basic_1() -> None:
    # todo maybe this should call stat or something instead?
    # would ensure reasonable stat implementation as well and less duplication
    from my.reddit.rexport import saved

    assert len(list(saved())) > 0


def test_basic_2() -> None:
    saves = list(my_reddit_rexport.saved())
    assert len(saves) > 0


def test_comments() -> None:
    assert len(list(my_reddit_all.comments())) > 0


def test_saves() -> None:
    from my.reddit.all import saved

    saves = list(saved())
    assert len(saves) > 0

    # will throw if not unique
    consume(ensure_unique(saves, key=lambda s: unwrap(s).id))


def test_comments_preserve_errors_and_deduplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    one, two, three = [my_reddit_rexport.Comment({'id': key}) for key in ('1', '2', '3')]
    first_error = ValueError('first bad export')
    last_error = ValueError('last bad export')
    monkeypatch.setattr(my_reddit_all, '_rexport_comments', lambda: iter([one, first_error, two]))
    monkeypatch.setattr(my_reddit_all, '_pushshift_comments', lambda: iter([one, first_error, three, last_error]))

    assert list(my_reddit_all.comments()) == [one, first_error, two, first_error, three, last_error]


@pytest.fixture(autouse=True, scope='module')
def prepare():
    data = testdata() / 'hpi-testdata' / 'reddit'
    assert data.exists(), data

    class reddit:
        class rexport:
            export_path = data

    with tmp_config() as cfg, disabled_cachew():
        cfg.reddit = reddit
        yield
