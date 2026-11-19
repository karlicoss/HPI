import warnings
from pathlib import Path
from typing import Literal

import pytest


@pytest.mark.parametrize('setting', ['export_path', 'export_dir', 'both'])
def test_export_path_and_legacy_export_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, setting: Literal['export_path', 'export_dir', 'both']
) -> None:
    """Resolve old configs with a migration warning and prefer export_path when both names exist."""
    import my.config
    import my.pinboard as pinboard

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
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        assert list(pinboard.inputs()) == [expected]

    if setting == 'export_dir':
        assert [str(w.message) for w in caught] == [
            'my.config.pinboard.export_dir is deprecated; rename it to my.config.pinboard.export_path'
        ]
    else:
        assert caught == []
