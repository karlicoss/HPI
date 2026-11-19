import warnings
from pathlib import Path

import pytest

import my.config
import my.instapaper.instapexport as provider
from my.core import __NOT_HPI_MODULE__  # noqa: F401


def test_config_migration(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing nested section triggers the warning even when the flat export path is missing too."""
    old_export = tmp_path / 'old.json'
    new_export = tmp_path / 'new.json'
    new_export.touch()

    class flat:
        export_path = old_export

    monkeypatch.setattr(my.config, 'instapaper', flat)
    with pytest.warns(UserWarning, match=r'Use my\.config\.instapaper\.instapexport\.export_path'):
        config = provider.make_config()
    assert config.export_path == old_export

    monkeypatch.delattr(flat, 'export_path')
    with pytest.warns(UserWarning, match='instapexport'), pytest.raises(AttributeError, match='export_path'):
        provider.inputs()

    class nested:
        export_path = old_export

        class instapexport:
            export_path = new_export

    monkeypatch.setattr(my.config, 'instapaper', nested)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        assert list(provider.inputs()) == [new_export]
