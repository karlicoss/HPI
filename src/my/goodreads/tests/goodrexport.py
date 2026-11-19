import warnings
from importlib import import_module
from pathlib import Path

import pytest

from my.core import __NOT_HPI_MODULE__  # noqa: F401
from my.core.cfg import tmp_config


@pytest.mark.parametrize('setting', ['nested', 'export_path', 'export_dir'])
def test_goodrexport_config(tmp_path: Path, setting: str) -> None:
    """The nested section wins, and either flat setting points users directly to its replacement."""
    shelf = tmp_path / 'shelf.xml'
    shelf.touch()

    class config:
        class goodreads:
            if setting == 'nested':
                export_path = tmp_path / 'unused.xml'

                class goodrexport:
                    export_path = shelf

            elif setting == 'export_path':
                export_path = shelf
            else:
                export_dir = shelf

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with tmp_config(modules=r'my\.goodreads\.goodrexport', config=config):
            provider = import_module('my.goodreads.goodrexport')
            assert list(provider.inputs()) == [shelf]

    messages = [str(w.message) for w in caught if 'my.config.goodreads' in str(w.message)]
    if setting == 'nested':
        assert messages == []
    else:
        assert messages == [
            f'my.config.goodreads.{setting} is deprecated. Use my.config.goodreads.goodrexport.export_path instead.'
        ]
