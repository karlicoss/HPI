from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

import my.moves as moves
from my.core import Res

FIRST_DAY: dict[str, Any] = {
    "date": "20990101",
    "futureField": {"supportedLater": None},
    "segments": [
        {
            "type": "place",
            "startTime": "20990101T080000+0230",
            "endTime": "20990101T090000+0230",
            "place": {
                "id": 101,
                "name": "Example Place A",
                "location": {"lat": 11.25, "lon": 22.5},
            },
            "activities": [],
        },
        {
            "type": "move",
            "startTime": "20990101T090000+0230",
            "endTime": "20990101T091000+0230",
            "activities": [
                {
                    "activity": "walking",
                    "group": "walking",
                    "manual": False,
                    "startTime": "20990101T090000+0230",
                    "endTime": "20990101T091000+0230",
                    "duration": 600,
                    "distance": 750.5,
                    "steps": 900,
                    "calories": None,
                    "trackPoints": [
                        {"lat": 10.0, "lon": 20.0, "time": "20990101T090000Z"},
                        {"lat": 10.1, "lon": 20.1, "time": "20990101T091000-0430"},
                    ],
                },
                {
                    "activity": "cycling",
                    "group": "cycling",
                    "manual": True,
                    "duration": 300,
                    "distance": 1200,
                    "steps": None,
                    "calories": 25,
                },
            ],
        },
    ],
}

LAST_DAY: dict[str, Any] = {
    "date": "20990103",
    "segments": [{"type": "off", "startTime": None, "endTime": None}],
}


def build_moves_archive(
    path: Path,
    *,
    daily_members: dict[str, Any] | None = None,
    nested_names: tuple[str, ...] = ("arbitrary-export-name/json.zip",),
) -> Path:
    if daily_members is None:
        # Deliberately reverse insertion order to test deterministic reading.
        daily_members = {
            "json/daily/storyline/storyline_20990103.json": LAST_DAY,
            "json/daily/storyline/storyline_20990101.json": FIRST_DAY,
        }

    nested_buffer = io.BytesIO()
    with zipfile.ZipFile(nested_buffer, "w", zipfile.ZIP_DEFLATED) as nested:
        for name, value in daily_members.items():
            if isinstance(value, bytes):
                payload = value
            elif isinstance(value, list):
                payload = json.dumps(value).encode()
            else:
                payload = json.dumps([value]).encode()
            nested.writestr(name, payload)
        nested.writestr("json/full/storyline.json", b"not daily JSON")
        nested.writestr("json/weekly/storyline/storyline_2099-W01.json", b"ignored")
        nested.writestr("csv/daily/storyline/storyline_20990101.csv", b"ignored")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as outer:
        for name in nested_names:
            outer.writestr(name, nested_buffer.getvalue())
        outer.writestr("README.txt", "Synthetic Moves fixture")
    return path


@pytest.fixture
def archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    result = build_moves_archive(tmp_path / "moves.zip")
    monkeypatch.setattr(moves.config, "export_path", result)
    return result


def values[T](results: list[Res[T]]) -> list[T]:
    return [result for result in results if not isinstance(result, Exception)]


def errors[T](results: list[Res[T]]) -> list[Exception]:
    return [result for result in results if isinstance(result, Exception)]


def test_input_discovery_uses_configured_archive(archive: Path) -> None:
    assert tuple(moves.inputs()) == (archive,)


def test_nested_zip_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    no_nested = build_moves_archive(tmp_path / "none.zip", nested_names=())
    monkeypatch.setattr(moves.config, "export_path", no_nested)
    [error] = list(moves.days())
    assert isinstance(error, moves.MovesError)
    assert "found 0" in str(error)

    multiple = build_moves_archive(tmp_path / "multiple.zip", nested_names=("one/json.zip", "two/json.zip"))
    monkeypatch.setattr(moves.config, "export_path", multiple)
    [error] = list(moves.days())
    assert isinstance(error, moves.MovesError)
    assert "found 2" in str(error)


def test_daily_selection_ordering_and_source_reference(archive: Path) -> None:
    results = list(moves.days())
    assert not errors(results)
    parsed = values(results)
    assert [day.date.isoformat() for day in parsed] == ["2099-01-01", "2099-01-03"]
    assert parsed[0].source.archive == archive
    assert parsed[0].source.nested_archive == "arbitrary-export-name/json.zip"
    assert parsed[0].source.member.endswith("storyline_20990101.json")
    assert parsed[0].source.day_index == 0


def test_every_object_in_a_daily_member_is_yielded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = build_moves_archive(
        tmp_path / "two-days-one-member.zip",
        daily_members={"json/daily/storyline/storyline_20990101.json": [FIRST_DAY, LAST_DAY]},
    )
    monkeypatch.setattr(moves.config, "export_path", archive)
    parsed = values(list(moves.days()))
    assert [day.source.day_index for day in parsed] == [0, 1]
    assert [day.date.isoformat() for day in parsed] == ["2099-01-01", "2099-01-03"]


def test_lossless_raw_preservation(archive: Path) -> None:
    first, last = values(list(moves.days()))
    assert first.raw == FIRST_DAY
    assert last.raw == LAST_DAY
    assert first.raw["futureField"] == {"supportedLater": None}
    assert first.raw["segments"][1]["activities"][0]["calories"] is None
    assert first.raw["segments"][1]["startTime"] == "20990101T090000+0230"


def test_typed_accessors_and_untimed_manual_activity(archive: Path) -> None:
    first = values(list(moves.days()))[0]
    place, movement = list(first.segments())
    assert place.type == "place"
    assert place.place == FIRST_DAY["segments"][0]["place"]
    assert place.start is not None
    assert place.start.utcoffset() == timedelta(hours=2, minutes=30)

    walking, manual = list(movement.activities())
    assert (walking.activity, walking.group, walking.manual) == ("walking", "walking", False)
    assert (walking.duration, walking.distance, walking.steps, walking.calories) == (600, 750.5, 900, None)
    first_point, second_point = list(walking.trackpoints())
    assert (first_point.lat, first_point.lon) == (10.0, 20.0)
    assert first_point.time is not None
    assert first_point.time.utcoffset() == timedelta(0)
    assert second_point.time is not None
    assert second_point.time.utcoffset() == -timedelta(hours=4, minutes=30)
    assert manual.manual is True
    assert manual.start is None
    assert manual.end is None


def test_flattened_iterators_and_source_indices(archive: Path) -> None:
    segment_results = list(moves.segments())
    activity_results = list(moves.activities())
    point_results = list(moves.trackpoints())
    assert len(values(segment_results)) == 3
    assert len(values(activity_results)) == 2
    assert len(values(point_results)) == 2
    assert not errors(segment_results)
    assert not errors(activity_results)
    assert not errors(point_results)

    movement = values(segment_results)[1]
    manual = values(activity_results)[1]
    second_point = values(point_results)[1]
    assert movement.source.segment_index == 1
    assert (manual.source.segment_index, manual.source.activity_index) == (1, 1)
    assert (second_point.source.activity_index, second_point.source.trackpoint_index) == (0, 1)


def test_malformed_member_is_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = build_moves_archive(
        tmp_path / "malformed.zip",
        daily_members={
            "json/daily/storyline/storyline_20990103.json": LAST_DAY,
            "json/daily/storyline/storyline_20990102.json": b"{malformed",
            "json/daily/storyline/storyline_20990101.json": FIRST_DAY,
        },
    )
    monkeypatch.setattr(moves.config, "export_path", archive)

    results = list(moves.days())
    assert [day.date.isoformat() for day in values(results)] == ["2099-01-01", "2099-01-03"]
    [error] = errors(results)
    assert "storyline_20990102.json" in str(error)
    assert "JSONDecodeError" in str(error)


def test_structural_errors_and_missing_daily_members(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = build_moves_archive(
        tmp_path / "structural.zip",
        daily_members={
            "json/daily/storyline/storyline_20990101.json": b"{}",
            "json/daily/storyline/storyline_20990102.json": b"[null]",
        },
    )
    monkeypatch.setattr(moves.config, "export_path", archive)
    results = list(moves.days())
    assert len(errors(results)) == 2
    assert not values(results)

    no_daily = build_moves_archive(tmp_path / "no-daily.zip", daily_members={})
    monkeypatch.setattr(moves.config, "export_path", no_daily)
    [error] = list(moves.days())
    assert isinstance(error, moves.MovesError)
    assert "no daily storyline members" in str(error)


def test_stats_are_content_free(archive: Path) -> None:
    result = moves.stats()
    assert result == {"days": 2, "segments": 3, "activities": 2, "trackpoints": 2, "errors": 0}
    rendered = repr(result)
    assert "Example Place" not in rendered
    assert "10.0" not in rendered


def test_parsing_does_not_modify_archive(archive: Path) -> None:
    before_bytes = archive.read_bytes()
    before_hash = hashlib.sha256(before_bytes).hexdigest()
    list(moves.days())
    moves.stats()
    after_bytes = archive.read_bytes()
    assert after_bytes == before_bytes
    assert hashlib.sha256(after_bytes).hexdigest() == before_hash
