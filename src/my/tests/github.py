import json
from pathlib import Path

import pytest

from my.core import unwrap
from my.github import ghexport


def test_events_continue_after_bad_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            'id': key,
            'created_at': '2026-10-24T12:00:00Z',
            'type': 'WatchEvent',
            'repo': {'name': 'example/repo'},
            'payload': {},
        }
        for key in ('1', '2')
    ]
    first = tmp_path / 'first.json'
    first.write_text(json.dumps(rows[:1]))
    broken = tmp_path / 'broken.json'
    broken.write_text('{')
    last = tmp_path / 'last.json'
    last.write_text(json.dumps({'events': rows}))
    monkeypatch.setattr(ghexport.config, 'export_path', [first, broken, last])

    [one, error, two] = ghexport.events()

    assert isinstance(error, Exception)
    assert str(broken) in '\n'.join(error.__notes__)
    assert [unwrap(one).eid, unwrap(two).eid] == ['1', '2']
