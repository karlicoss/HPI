"""
Experimental snapshots and diffs for HPI provider output.

This module is a work in progress.
Neither its Python API nor its JSONL and metadata file formats are stable.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .query import locate_qualified_function
from .serialize import dumps as hpi_dumps

_FORMAT = 'hpi-provider-snapshot'
_FORMAT_VERSION = 1
_DATA_FORMAT = 'jsonl'
_MISSING = object()


@dataclass(frozen=True, kw_only=True)
class Snapshot:
    provider: str
    key: str | None
    created_at: datetime
    items: tuple[Any, ...]
    error_count: int


@dataclass(frozen=True, kw_only=True)
class SnapshotDiff:
    """Semantic comparison of a baseline snapshot and newly collected provider output."""

    before: Snapshot
    """Baseline snapshot loaded from disk."""

    after: Snapshot
    """New snapshot collected from the provider."""

    key: str | None
    """Item field used as the key; author.id means the id field inside author, and None compares sequences directly."""

    before_by_key: Mapping[str, tuple[Any, ...]]
    """Baseline items grouped by key, empty when key is None."""

    after_by_key: Mapping[str, tuple[Any, ...]]
    """New items grouped by key, empty when key is None."""

    unkeyed_before: tuple[Any, ...]
    """Baseline items where key is missing, or every baseline item when key is None."""

    unkeyed_after: tuple[Any, ...]
    """New items where key is missing, or every new item when key is None."""

    unchanged_keys: tuple[str, ...]
    """Keys found in both snapshots whose items are identical."""

    changed_keys: tuple[str, ...]
    """Keys found in both snapshots whose items differ."""

    added_keys: tuple[str, ...]
    """Keys present only in the new snapshot."""

    removed_keys: tuple[str, ...]
    """Keys present only in the baseline snapshot."""

    @property
    def duplicate_before_keys(self) -> tuple[str, ...]:
        return tuple(key for key, items in self.before_by_key.items() if len(items) > 1)

    @property
    def duplicate_after_keys(self) -> tuple[str, ...]:
        return tuple(key for key, items in self.after_by_key.items() if len(items) > 1)

    @property
    def added_revision_count(self) -> int:
        common_keys = self.before_by_key.keys() & self.after_by_key.keys()
        return sum(max(len(self.after_by_key[key]) - len(self.before_by_key[key]), 0) for key in common_keys)

    @property
    def removed_revision_count(self) -> int:
        common_keys = self.before_by_key.keys() & self.after_by_key.keys()
        return sum(max(len(self.before_by_key[key]) - len(self.after_by_key[key]), 0) for key in common_keys)

    @property
    def has_changes(self) -> bool:
        return (
            len(self.changed_keys) > 0
            or len(self.added_keys) > 0
            or len(self.removed_keys) > 0
            or self.unkeyed_before != self.unkeyed_after
            or self.before.error_count != self.after.error_count
        )


def _to_json_value(value: Any) -> Any:
    return json.loads(hpi_dumps(value))


def _pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _validate_key(*, key: str | None) -> None:
    if key is None:
        return
    assert all(part != '' for part in key.split('.')), key


def make_snapshot(
    *,
    provider: str,
    items: Iterable[Any],
    key: str | None = None,
    created_at: datetime | None = None,
) -> Snapshot:
    assert provider != '', provider
    _validate_key(key=key)

    if created_at is None:
        created_at = datetime.now(tz=UTC)
    assert created_at.tzinfo is not None, created_at

    json_items: list[Any] = []
    error_count = 0
    for item in items:
        if isinstance(item, Exception):
            error_count += 1
        json_items.append(_to_json_value(item))

    return Snapshot(
        provider=provider,
        key=key,
        created_at=created_at,
        items=tuple(json_items),
        error_count=error_count,
    )


def snapshot_provider(*, provider: str, key: str | None = None) -> Snapshot:
    function = locate_qualified_function(provider)
    return make_snapshot(provider=provider, items=function(), key=key)


def _snapshot_metadata_to_json(snapshot: Snapshot) -> dict[str, Any]:
    return {
        'format': _FORMAT,
        'format_version': _FORMAT_VERSION,
        'data_format': _DATA_FORMAT,
        'provider': snapshot.provider,
        'key': snapshot.key,
        'created_at': snapshot.created_at.isoformat(),
        'stats': {
            'items': len(snapshot.items),
            'errors': snapshot.error_count,
        },
    }


def snapshot_metadata_path(*, path: Path) -> Path:
    return path.with_name(f'{path.name}.meta.json')


def write_snapshot(*, snapshot: Snapshot, path: Path, overwrite: bool = False) -> None:
    metadata_path = snapshot_metadata_path(path=path)
    if not overwrite:
        for output_path in (path, metadata_path):
            if output_path.exists():
                raise FileExistsError(output_path)

    mode = 'w' if overwrite else 'x'
    with path.open(mode=mode) as fo:
        for item in snapshot.items:
            print(_canonical_json(item), file=fo)

    with metadata_path.open(mode=mode) as fo:
        print(_pretty_json(_snapshot_metadata_to_json(snapshot)), file=fo)


def _load_jsonl(*, path: Path) -> tuple[Any, ...]:
    items: list[Any] = []
    with path.open() as fo:
        for line_number, line in enumerate(fo, start=1):
            assert line.strip() != '', (path, line_number)
            items.append(json.loads(line))
    return tuple(items)


def _is_serialized_error(item: Any) -> bool:
    return isinstance(item, dict) and set(item) == {'error'} and isinstance(item['error'], str)


def load_snapshot(
    *,
    path: Path,
    fallback_provider: str | None = None,
    fallback_key: str | None = None,
) -> Snapshot:
    items = _load_jsonl(path=path)
    metadata_path = snapshot_metadata_path(path=path)
    if not metadata_path.exists():
        assert fallback_provider is not None, path
        assert fallback_provider != '', fallback_provider
        _validate_key(key=fallback_key)
        created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        error_count = sum(1 for item in items if _is_serialized_error(item))
        return Snapshot(
            provider=fallback_provider,
            key=fallback_key,
            created_at=created_at,
            items=items,
            error_count=error_count,
        )

    data = json.loads(metadata_path.read_text())
    assert isinstance(data, dict), data
    assert data['format'] == _FORMAT, data['format']
    assert data['format_version'] == _FORMAT_VERSION, data['format_version']
    assert data['data_format'] == _DATA_FORMAT, data['data_format']

    provider = data['provider']
    assert isinstance(provider, str), provider
    assert provider != '', provider

    key = data['key']
    assert key is None or (isinstance(key, str) and key != ''), key
    _validate_key(key=key)

    created_at = datetime.fromisoformat(data['created_at'])
    assert created_at.tzinfo is not None, created_at

    stats = data['stats']
    assert isinstance(stats, dict), stats
    item_count = stats['items']
    error_count = stats['errors']
    assert type(item_count) is int, item_count
    assert item_count >= 0, item_count
    assert type(error_count) is int, error_count
    assert error_count >= 0, error_count
    assert item_count == len(items), (item_count, len(items))
    assert error_count <= item_count, (error_count, item_count)

    return Snapshot(
        provider=provider,
        key=key,
        created_at=created_at,
        items=items,
        error_count=error_count,
    )


def _extract_key(*, item: Any, key: str) -> Any:
    current = item
    for part in key.split('.'):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _canonical_key(value: Any) -> str:
    return _canonical_json(value)


def _group_by_key(*, items: Iterable[Any], key: str | None) -> tuple[dict[str, tuple[Any, ...]], tuple[Any, ...]]:
    if key is None:
        return {}, tuple(items)

    grouped: dict[str, list[Any]] = {}
    unkeyed: list[Any] = []
    for item in items:
        value = _extract_key(item=item, key=key)
        if value is _MISSING:
            unkeyed.append(item)
            continue
        canonical_key = _canonical_key(value)
        grouped.setdefault(canonical_key, []).append(item)

    return {key: tuple(values) for key, values in grouped.items()}, tuple(unkeyed)


def compare_snapshots(*, before: Snapshot, after: Snapshot, key: str | None = None) -> SnapshotDiff:
    if key is None:
        assert before.key == after.key, (before.key, after.key)
        key = before.key
    _validate_key(key=key)

    before_by_key, unkeyed_before = _group_by_key(items=before.items, key=key)
    after_by_key, unkeyed_after = _group_by_key(items=after.items, key=key)

    before_keys = before_by_key.keys()
    after_keys = after_by_key.keys()
    common_keys = before_keys & after_keys

    unchanged_keys = tuple(sorted(key for key in common_keys if before_by_key[key] == after_by_key[key]))
    changed_keys = tuple(sorted(key for key in common_keys if before_by_key[key] != after_by_key[key]))
    added_keys = tuple(sorted(after_keys - before_keys))
    removed_keys = tuple(sorted(before_keys - after_keys))

    return SnapshotDiff(
        before=before,
        after=after,
        key=key,
        before_by_key=before_by_key,
        after_by_key=after_by_key,
        unkeyed_before=unkeyed_before,
        unkeyed_after=unkeyed_after,
        unchanged_keys=unchanged_keys,
        changed_keys=changed_keys,
        added_keys=added_keys,
        removed_keys=removed_keys,
    )


def _unified_diff(*, before: Any, after: Any, label: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix='hpi-unified-diff-') as temp_dir:
        before_path = Path(temp_dir) / 'before.json'
        after_path = Path(temp_dir) / 'after.json'
        before_path.write_text(f'{_pretty_json(before)}\n')
        after_path.write_text(f'{_pretty_json(after)}\n')
        result = subprocess.run(
            [
                'diff', '-u',
                # replace temporary filename in the diff header with a stable before/after name.
                '--label', f'before:{label}',
                '--label', f'after:{label}',
                str(before_path),
                str(after_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )  # fmt: skip
    assert result.returncode in (0, 1), result
    return result.stdout.splitlines()


def _summary_rows(*, diff: SnapshotDiff) -> list[tuple[str, str]]:
    provider = diff.before.provider
    if diff.before.provider != diff.after.provider:
        provider = f'{diff.before.provider} -> {diff.after.provider}'

    rows = [
        ('status', 'changed' if diff.has_changes else 'unchanged'),
        ('provider', provider),
        ('key', diff.key if diff.key is not None else '<sequence>'),
        ('items', f'{len(diff.before.items)} -> {len(diff.after.items)}'),
        ('errors', f'{diff.before.error_count} -> {diff.after.error_count}'),
    ]
    if diff.key is not None:
        rows.extend(
            [
                ('unchanged keys', str(len(diff.unchanged_keys))),
                ('changed keys', str(len(diff.changed_keys))),
                ('added keys', str(len(diff.added_keys))),
                ('removed keys', str(len(diff.removed_keys))),
                ('new revisions of old keys', str(diff.added_revision_count)),
                ('removed revisions of old keys', str(diff.removed_revision_count)),
                ('duplicate keys before', str(len(diff.duplicate_before_keys))),
                ('duplicate keys after', str(len(diff.duplicate_after_keys))),
                ('unkeyed items', f'{len(diff.unkeyed_before)} -> {len(diff.unkeyed_after)}'),
            ]
        )
    return rows


def format_summary(*, diff: SnapshotDiff) -> str:
    rows = _summary_rows(diff=diff)
    width = max(len(label) for label, _value in rows)
    lines = [f'{label + ":":<{width + 1}} {value}' for label, value in rows]
    return '\n'.join(lines)


def format_diff_details(*, diff: SnapshotDiff) -> str:
    before, after = make_diff_documents(diff=diff)
    label = diff.key if diff.key is not None else 'items'
    detail_lines = _unified_diff(before=before, after=after, label=label)

    if len(detail_lines) == 0:
        return ''
    return '\n'.join(('Details:', *detail_lines))


def format_diff(*, diff: SnapshotDiff, details: bool = True) -> str:
    summary = format_summary(diff=diff)
    if not details or not diff.has_changes:
        return summary

    formatted_details = format_diff_details(diff=diff)
    if formatted_details == '':
        return summary
    return f'{summary}\n\n{formatted_details}'


def make_diff_documents(*, diff: SnapshotDiff) -> tuple[Any, Any]:
    if diff.key is None:
        return diff.unkeyed_before, diff.unkeyed_after

    detail_keys = sorted(set(diff.changed_keys) | set(diff.added_keys) | set(diff.removed_keys))

    def make_document(*, by_key: Mapping[str, tuple[Any, ...]], unkeyed: tuple[Any, ...]) -> dict[str, Any]:
        groups = [
            {
                'key': json.loads(item_key),
                'items': by_key.get(item_key, ()),
            }
            for item_key in detail_keys
        ]
        return {
            'identity_key': diff.key,
            'groups': groups,
            'unkeyed_items': unkeyed if diff.unkeyed_before != diff.unkeyed_after else (),
        }

    before = make_document(by_key=diff.before_by_key, unkeyed=diff.unkeyed_before)
    after = make_document(by_key=diff.after_by_key, unkeyed=diff.unkeyed_after)
    return before, after


def write_diff_documents(*, diff: SnapshotDiff, before_path: Path, after_path: Path) -> bool:
    assert before_path != after_path, before_path
    before, after = make_diff_documents(diff=diff)
    before_path.write_text(f'{_pretty_json(before)}\n')
    after_path.write_text(f'{_pretty_json(after)}\n')
    return before != after
