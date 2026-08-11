from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from my.core.__main__ import main
from my.core._snapshot import (
    compare_snapshots,
    format_diff,
    load_snapshot,
    make_snapshot,
    snapshot_metadata_path,
    write_snapshot,
)


def snapshot_test_provider() -> list[dict[str, str]]:
    return [
        {'id': '1', 'value': 'current'},
        {'id': '2', 'value': 'unchanged'},
    ]


def _decoded_keys(keys: tuple[str, ...]) -> tuple[object, ...]:
    return tuple(json.loads(key) for key in keys)


def test_snapshot_roundtrip(tmp_path: Path) -> None:
    """Round-trip a snapshot and verify its JSONL, metadata, and overwrite behavior."""
    created_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    snapshot = make_snapshot(
        provider='my.example.items',
        key='id',
        created_at=created_at,
        items=[
            {'value': 'first', 'id': '1'},
            RuntimeError('broken item'),
        ],
    )
    path = tmp_path / 'snapshot.jsonl'
    write_snapshot(snapshot=snapshot, path=path)

    assert load_snapshot(path=path) == snapshot
    assert path.read_text().splitlines()[0] == '{"id":"1","value":"first"}'

    metadata_path = snapshot_metadata_path(path=path)
    metadata = json.loads(metadata_path.read_text())
    assert metadata['stats'] == {'errors': 1, 'items': 2}

    with pytest.raises(FileExistsError):
        write_snapshot(snapshot=snapshot, path=path)

    write_snapshot(snapshot=snapshot, path=path, overwrite=True)
    assert load_snapshot(path=path) == snapshot


def test_malformed_key() -> None:
    with pytest.raises(AssertionError):
        make_snapshot(provider='my.example.items', key='author..id', items=[])


def test_keyed_diff() -> None:
    """Classify keyed changes and duplicate revisions, then render their details."""
    created_at = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    before = make_snapshot(
        provider='my.example.items',
        key='id',
        created_at=created_at,
        items=[
            {'id': 'question', 'text': 'Question only'},
            {'id': 'same', 'text': 'Unchanged'},
            {'id': 'removed', 'text': 'Removed'},
        ],
    )
    after = make_snapshot(
        provider='my.example.items',
        key='id',
        created_at=created_at,
        items=[
            {'id': 'question', 'text': 'Question\nMy answer\nTheir answer: '},
            {'id': 'question', 'text': 'Question\nMy answer\nTheir answer: Answered'},
            {'id': 'same', 'text': 'Unchanged'},
            {'id': 'added', 'text': 'Added'},
        ],
    )

    diff = compare_snapshots(before=before, after=after)
    assert _decoded_keys(diff.unchanged_keys) == ('same',)
    assert _decoded_keys(diff.changed_keys) == ('question',)
    assert _decoded_keys(diff.added_keys) == ('added',)
    assert _decoded_keys(diff.removed_keys) == ('removed',)
    assert diff.added_revision_count == 1
    assert _decoded_keys(diff.duplicate_before_keys) == ()
    assert _decoded_keys(diff.duplicate_after_keys) == ('question',)
    assert diff.has_changes

    formatted = format_diff(diff=diff)
    assert any(line.startswith('status:') and line.endswith('changed') for line in formatted.splitlines())
    assert '--- before:id' in formatted
    assert '+++ after:id' in formatted
    assert 'Their answer: Answered' in formatted


def test_dev_snapshot_cli_without_key(tmp_path: Path) -> None:
    provider = 'my.core.tests.test_snapshot.snapshot_test_provider'
    path = tmp_path / 'snapshot.jsonl'
    runner = CliRunner()

    captured = runner.invoke(main, ['dev', 'snapshot', '--output', str(path), provider])
    assert captured.exit_code == 0, captured.output
    assert 'Wrote 2 items (0 errors)' in captured.output
    assert 'snapshot.jsonl.meta.json' in captured.output
    assert snapshot_metadata_path(path=path).exists()

    unchanged = runner.invoke(main, ['dev', 'diff', '--no-details', str(path)])
    assert unchanged.exit_code == 0, unchanged.output
    assert any(line.startswith('status:') and line.endswith('unchanged') for line in unchanged.output.splitlines())

    before = make_snapshot(
        provider=provider,
        items=[
            {'id': '1', 'value': 'before'},
        ],
    )
    write_snapshot(snapshot=before, path=path, overwrite=True)

    changed = runner.invoke(main, ['dev', 'diff', str(path)])
    assert changed.exit_code == 1, changed.output
    assert any(line.startswith('status:') and line.endswith('changed') for line in changed.output.splitlines())
    assert any(line.startswith('items:') and line.endswith('1 -> 2') for line in changed.output.splitlines())


def test_dev_diff_query_stream_jsonl(tmp_path: Path) -> None:
    """Compare raw `hpi query --stream` JSONL without a snapshot metadata sidecar."""
    provider = 'my.core.tests.test_snapshot.snapshot_test_provider'
    path = tmp_path / 'query.jsonl'
    runner = CliRunner()

    query = runner.invoke(main, ['query', '--stream', provider])
    assert query.exit_code == 0, query.output
    path.write_text(query.output)
    assert not snapshot_metadata_path(path=path).exists()

    missing_provider = runner.invoke(main, ['dev', 'diff', '--no-details', str(path)])
    assert missing_provider.exit_code == 2, missing_provider.output
    assert 'FUNCTION_NAME is required' in missing_provider.output

    unchanged = runner.invoke(main, ['dev', 'diff', '--no-details', '--key', 'id', str(path), provider])
    assert unchanged.exit_code == 0, unchanged.output
    assert any(line.startswith('status:') and line.endswith('unchanged') for line in unchanged.output.splitlines())
