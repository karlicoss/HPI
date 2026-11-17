from dataclasses import replace
from datetime import datetime
from inspect import unwrap
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from emfitexport.tests.test_dal import FakeData
from hpikit.datetime import aware

import my.emfit.emfitexport as api
from my.core import __NOT_HPI_MODULE__  # noqa: F401


@pytest.mark.parametrize('day', ['2020-03-29', '2020-10-25'], ids=['spring-forward', 'fall-back'])
def test_dataframe_elapsed_duration_across_dst(*, day: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """An hour of elapsed sleep stays an hour when displayed across either London clock change."""
    london = ZoneInfo('Europe/London')
    start = datetime.fromisoformat(f'{day}T00:30:00+00:00').astimezone(london)
    end = datetime.fromisoformat(f'{day}T01:30:00+00:00').astimezone(london)
    sleep = replace(
        api.Emfit.from_json(FakeData().generate()),
        start=aware(start),
        end=aware(end),
        sleep_start=aware(start),
        sleep_end=aware(end),
    )
    monkeypatch.setattr(api, 'datas', lambda: [sleep])

    [row] = api.dataframe().to_dict(orient='records')
    assert row['bed_time'] == 60
    assert row['sleep_start'] == start
    assert row['sleep_end'] == end


def test_cache_follows_config_changes(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing the timezone or exclusions must take effect without modifying the exports."""
    from cachew import settings

    from my.core.cachew import mcachew

    monkeypatch.setattr(settings, 'ENABLE', True)
    with api.fake_data(nights=1) as cfg:
        cached_datas = mcachew(cache_path=tmp_path / 'cache', depends_on=api._cachew_depends_on)(unwrap(api.datas))
        [initial] = cached_datas()

        cfg.emfit.timezone = ZoneInfo('Pacific/Honolulu')
        [localized] = cached_datas()
        assert localized.sleep_start.isoformat() == initial.sleep_start.astimezone(cfg.emfit.timezone).isoformat()

        cfg.emfit.excluded_sids = (initial.sid,)
        assert list(cached_datas()) == []
