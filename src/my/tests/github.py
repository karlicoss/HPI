import io
import json
import tarfile
from pathlib import Path

from my.core import unwrap
from my.core.cfg import tmp_config
from my.github import gdpr, ghexport


def test_events_continue_after_bad_file(tmp_path: Path) -> None:
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

    class github:
        export_path = (first, broken, last)

    with tmp_config() as cfg:
        cfg.github = github
        [one, error, two] = ghexport.events()

    assert isinstance(error, Exception)
    assert str(broken) in '\n'.join(error.__notes__)
    assert [unwrap(one).eid, unwrap(two).eid] == ['1', '2']


def _push(*, eid: str, dts: str, push_id: int, head: str, full: bool) -> dict:
    payload: dict = {'push_id': push_id, 'ref': 'refs/heads/master', 'before': 'a' * 40, 'head': head}
    if full:
        payload['commits'] = [{'message': 'fix things'}]
    return {'id': eid, 'created_at': dts, 'type': 'PushEvent', 'repo': {'name': 'user/repo'}, 'payload': payload}


def _pr(*, eid: str, dts: str, pr_id: int, number: int, full: bool) -> dict:
    pr: dict = {'id': pr_id, 'number': number, 'url': f'https://api.github.com/repos/user/repo/pulls/{number}'}
    if full:
        pr |= {'title': 'add feature', 'html_url': f'https://github.com/user/repo/pull/{number}', 'body': 'details'}
    payload = {'action': 'opened', 'number': number, 'pull_request': pr}
    return {'id': eid, 'created_at': dts, 'type': 'PullRequestEvent', 'repo': {'name': 'user/repo'}, 'payload': payload}


def test_events_trimmed_payloads(tmp_path: Path) -> None:
    older = tmp_path / 'older.json'
    older.write_text(json.dumps({'events': [
        _push(eid='50', dts='2025-08-10T16:45:11Z', push_id=1, head='b' * 40, full=True),
        _pr  (eid='51', dts='2025-08-10T17:00:55Z', pr_id=10, number=5, full=True),
    ]}))  # fmt: skip
    newer = tmp_path / 'newer.json'
    newer.write_text(json.dumps({'events': [
        # copies of the events above, re-issued by github under new ids
        _push(eid='3', dts='2025-08-10T16:45:10Z', push_id=1, head='b' * 40, full=False),
        _pr  (eid='4', dts='2025-08-10T17:00:54Z', pr_id=10, number=5, full=False),
        _push(eid='5', dts='2025-10-10T12:00:00Z', push_id=2, head='c' * 40, full=False),
        _pr  (eid='6', dts='2025-10-10T12:00:00Z', pr_id=11, number=6, full=False),
    ]}))  # fmt: skip

    class github:
        export_path = (older, newer)

    with tmp_config() as cfg:
        cfg.github = github
        events = [unwrap(e) for e in ghexport.events()]

    assert [(e.summary, e.link) for e in events] == [
        ('user/repo: pushed 1 commits to refs/heads/master', None),
        ('user/repo: opened PR: add feature', 'https://github.com/user/repo/pull/5'),
        ('user/repo: pushed to refs/heads/master', 'https://github.com/user/repo/compare/aaaaaaaaaaaa...cccccccccccc'),
        ('user/repo: opened PR: #6', 'https://github.com/user/repo/pull/6'),
    ]


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
