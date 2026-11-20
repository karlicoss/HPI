from pathlib import Path

import pytest

import my.config
import my.endomondo.endoexport as provider
from my.core import __NOT_HPI_MODULE__  # noqa: F401


@pytest.mark.filterwarnings('error:The flat Endomondo config is deprecated')
def test_fake_data_restores_flat_config(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The demo uses its nested config, then restores the caller's flat export."""
    saved = tmp_path / 'workouts.json'
    saved.write_text('[]')

    class flat:
        export_path = saved

    monkeypatch.setattr(my.config, 'endomondo', flat)
    with provider.fake_data(count=1):
        [workout] = provider.workouts()
        assert isinstance(workout, provider.Workout)

    with pytest.warns(UserWarning, match=r'Use my\.config\.endomondo\.endoexport\.export_path'):
        assert list(provider.workouts()) == []
