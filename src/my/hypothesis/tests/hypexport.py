from pathlib import Path

import pytest

from my.core import __NOT_HPI_MODULE__  # noqa: F401
from my.core.cfg import tmp_config
from my.hypothesis.hypexport import inputs


def test_override_config_via_old_module_name(*, tmp_path: Path) -> None:
    """Promnesia reloads only my.hypothesis when overriding the config of an already imported provider."""
    flat_file = tmp_path / 'old.json'
    nested_file = tmp_path / 'new.json'
    flat_file.touch()
    nested_file.touch()

    class flat:
        class hypothesis:
            export_path = flat_file

    class nested:
        class hypothesis:
            export_path = flat_file

            class hypexport:
                export_path = nested_file

    with tmp_config(modules='my.hypothesis', config=nested):
        assert list(inputs()) == [nested_file]
        with tmp_config(modules='my.hypothesis', config=flat):
            with pytest.warns(UserWarning, match=r'Use my\.config\.hypothesis\.hypexport\.export_path'):
                assert list(inputs()) == [flat_file]
        assert list(inputs()) == [nested_file]
