from pathlib import Path

import pytest

import my.config
import my.goodreads.goodrexport as provider
from my.core import __NOT_HPI_MODULE__  # noqa: F401


@pytest.mark.filterwarnings('error:The flat Goodreads config is deprecated')
def test_goodrexport_config(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the flat config warns, and a nested export path takes precedence."""
    shelf = tmp_path / 'shelf.xml'
    shelf.touch()

    class flat:
        export_path = shelf

    monkeypatch.setattr(my.config, 'goodreads', flat)
    with pytest.warns(UserWarning, match=r'Use my\.config\.goodreads\.goodrexport\.export_path'):
        assert list(provider.inputs()) == [shelf]

    class nested:
        export_path = tmp_path / 'unused.xml'

        class goodrexport:
            export_path = shelf

    monkeypatch.setattr(my.config, 'goodreads', nested)
    assert list(provider.inputs()) == [shelf]
