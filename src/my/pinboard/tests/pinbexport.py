from pathlib import Path
from typing import Literal

import pytest

import my.config
import my.pinboard.pinbexport as pinboard
from my.core import __NOT_HPI_MODULE__  # noqa: F401


@pytest.mark.parametrize('setting', ['export_path', 'export_dir', 'both'])
def test_flat_config(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setting: Literal['export_path', 'export_dir', 'both']
) -> None:
    """Both flat spellings warn once, and export_path takes precedence when both are set."""
    expected = tmp_path / 'expected.json'
    ignored = tmp_path / 'ignored.json'
    expected.touch()
    ignored.touch()

    class user_config:
        if setting != 'export_path':
            export_dir = expected if setting == 'export_dir' else ignored
        if setting != 'export_dir':
            export_path = expected

    monkeypatch.setattr(my.config, 'pinboard', user_config)
    with pytest.warns(UserWarning, match=r'Use my\.config\.pinboard\.pinbexport\.export_path') as caught:
        assert list(pinboard.inputs()) == [expected]
    assert len(caught) == 1
