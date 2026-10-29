import io
import json
import tarfile
from pathlib import Path

import pytest

from my.core import unwrap
from my.core.cfg import tmp_config
from my.github import gdpr, ghexport


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


def _gdpr_archive(path: Path, *, repo: str) -> Path:
    repos = [{'url': f'https://github.com/{repo}', 'created_at': '2020-01-01T00:00:00Z', 'type': 'repository'}]
    data = json.dumps(repos).encode()
    info = tarfile.TarInfo('repositories_000001.json')
    info.size = len(data)
    with tarfile.open(path, 'w:gz') as tf:
        tf.addfile(info, io.BytesIO(data))
    return path


def test_gdpr_uses_last_input(tmp_path: Path) -> None:
    # names deliberately don't sort in the configured order
    newer = _gdpr_archive(tmp_path / 'a.tar.gz', repo='user/newer')
    older = _gdpr_archive(tmp_path / 'b.tar.gz', repo='user/older')

    class github:
        gdpr_dir = (older, newer)

    with tmp_config() as cfg:
        cfg.github = github
        [event] = gdpr.events()
    assert unwrap(event).summary == 'created user/newer'
