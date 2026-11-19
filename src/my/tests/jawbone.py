import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


@pytest.mark.parametrize(
    ('start', 'end', 'local_start', 'local_end', 'end_fold'),
    [
        (
            '2020-03-29T00:30:00+00:00',
            '2020-03-29T01:30:00+00:00',
            '2020-03-29T00:30:00+00:00',
            '2020-03-29T02:30:00+01:00',
            0,
        ),
        (
            '2020-10-25T00:30:00+00:00',
            '2020-10-25T01:30:00+00:00',
            '2020-10-25T01:30:00+01:00',
            '2020-10-25T01:30:00+00:00',
            1,
        ),
    ],
    ids=['spring-forward', 'fall-back'],
)
def test_elapsed_sleep_duration_across_dst(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    start: str,
    end: str,
    local_start: str,
    local_end: str,
    end_fold: int,
) -> None:
    import my.config
    import my.jawbone.api as api

    class user_config:
        export_path = tmp_path

    monkeypatch.setattr(my.config, 'jawbone', user_config)
    (tmp_path / 'sleeps.json').write_text(
        json.dumps(
            [
                {
                    'xid': 'sleep',
                    'title': 'Sleep across a clock change',
                    'details': {
                        'tz': 'Europe/London',
                        'asleep_time': int(datetime.fromisoformat(start).timestamp()),
                        'awake_time': int(datetime.fromisoformat(end).timestamp()),
                    },
                }
            ]
        )
    )

    [sleep] = api.load_sleeps()
    assert sleep.sleep_start.isoformat() == local_start
    assert sleep.sleep_end.isoformat() == local_end
    assert sleep.sleep_start.tzinfo is ZoneInfo('Europe/London')
    assert sleep.sleep_start.fold == 0
    assert sleep.sleep_end.fold == end_fold
    assert sleep.bed_time == 60


def test_export_directory_changes_refresh_sleep_and_phase_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import my.config
    import my.jawbone.api as api

    first = tmp_path / 'first'
    second = tmp_path / 'second'
    for root, timestamp in [(first, 1), (second, 2)]:
        root.mkdir()
        (root / 'sleeps.json').write_text(
            json.dumps(
                [
                    {
                        'xid': 'same-id',
                        'title': root.name,
                        'details': {'tz': 'UTC'},
                    }
                ]
            )
        )
        (root / 'phases.json').write_text(json.dumps({'same-id': [{'time': timestamp}]}))

    current_dir: Path | str = first

    class user_config:
        @property
        def export_path(self) -> Path | str:
            return current_dir

    monkeypatch.setattr(my.config, 'jawbone', user_config)
    [sleep] = api.load_sleeps()
    assert sleep.title == 'first'
    assert sleep.graph == first / 'graphs' / 'same-id.png'
    assert sleep.phases == [datetime.fromtimestamp(1, tz=UTC)]

    current_dir = str(second)
    [sleep] = api.load_sleeps()
    assert sleep.title == 'second'
    assert sleep.graph == second / 'graphs' / 'same-id.png'
    assert sleep.phases == [datetime.fromtimestamp(2, tz=UTC)]
