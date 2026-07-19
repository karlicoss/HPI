"""
Source-faithful access to a [[https://en.wikipedia.org/wiki/Moves_(app)][Moves]] export.

Only daily storyline JSON is parsed. The configured outer ZIP remains the
authority; objects returned here retain the complete decoded JSON and source
provenance.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from my.config import moves as user_config
from my.core import Res, Stats, get_files, make_config


@dataclass
class moves(user_config):
    """Uses the outer ZIP produced by Moves' data export."""

    export_path: Path | str


config = make_config(moves)

_DAILY_STORYLINE = re.compile(r"^json/daily/storyline/storyline_\d{8}\.json$")


class MovesError(Exception):
    """An error tied to a Moves archive or one of its members."""


@dataclass(frozen=True)
class SourceRef:
    archive: Path
    nested_archive: str
    member: str
    day_index: int
    segment_index: int | None = None
    activity_index: int | None = None
    trackpoint_index: int | None = None


def _timestamp(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%S%z")
    except ValueError as error:
        raise ValueError(f"invalid Moves timestamp: {value!r}") from error


def _optional_timestamp(raw: Mapping[str, Any], key: str) -> datetime | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Moves {key} must be a string or null")
    return _timestamp(value)


def _optional_number(raw: Mapping[str, Any], key: str) -> int | float | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"Moves {key} must be numeric or null")
    return value


@dataclass(frozen=True)
class Day:
    raw: dict[str, Any]
    source: SourceRef

    @property
    def date(self) -> Date:
        value = self.raw.get("date")
        if not isinstance(value, str):
            raise TypeError("Moves day date must be a string")
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError as error:
            raise ValueError(f"invalid Moves date: {value!r}") from error

    def segments(self) -> Iterator[Segment]:
        values = self.raw.get("segments", [])
        if not isinstance(values, list):
            raise TypeError("Moves day segments must be an array")
        for index, raw in enumerate(values):
            if not isinstance(raw, dict):
                raise TypeError(f"Moves segment {index} must be an object")
            raw = cast(dict[str, Any], raw)
            yield Segment(
                raw=raw,
                source=SourceRef(
                    archive=self.source.archive,
                    nested_archive=self.source.nested_archive,
                    member=self.source.member,
                    day_index=self.source.day_index,
                    segment_index=index,
                ),
            )


@dataclass(frozen=True)
class Segment:
    raw: dict[str, Any]
    source: SourceRef

    @property
    def type(self) -> str | None:
        value = self.raw.get("type")
        if value is not None and not isinstance(value, str):
            raise TypeError("Moves segment type must be a string or null")
        return value

    @property
    def start(self) -> datetime | None:
        return _optional_timestamp(self.raw, "startTime")

    @property
    def end(self) -> datetime | None:
        return _optional_timestamp(self.raw, "endTime")

    @property
    def place(self) -> dict[str, Any] | None:
        value = self.raw.get("place")
        if value is not None and not isinstance(value, dict):
            raise TypeError("Moves segment place must be an object or null")
        return value

    def activities(self) -> Iterator[Activity]:
        values = self.raw.get("activities", [])
        if not isinstance(values, list):
            raise TypeError("Moves segment activities must be an array")
        for index, raw in enumerate(values):
            if not isinstance(raw, dict):
                raise TypeError(f"Moves activity {index} must be an object")
            raw = cast(dict[str, Any], raw)
            yield Activity(
                raw=raw,
                source=SourceRef(
                    archive=self.source.archive,
                    nested_archive=self.source.nested_archive,
                    member=self.source.member,
                    day_index=self.source.day_index,
                    segment_index=self.source.segment_index,
                    activity_index=index,
                ),
            )


@dataclass(frozen=True)
class Activity:
    raw: dict[str, Any]
    source: SourceRef

    @property
    def activity(self) -> str | None:
        value = self.raw.get("activity")
        if value is not None and not isinstance(value, str):
            raise TypeError("Moves activity classification must be a string or null")
        return value

    @property
    def group(self) -> str | None:
        value = self.raw.get("group")
        if value is not None and not isinstance(value, str):
            raise TypeError("Moves activity group must be a string or null")
        return value

    @property
    def manual(self) -> bool | None:
        value = self.raw.get("manual")
        if value is not None and not isinstance(value, bool):
            raise TypeError("Moves activity manual flag must be boolean or null")
        return value

    @property
    def start(self) -> datetime | None:
        return _optional_timestamp(self.raw, "startTime")

    @property
    def end(self) -> datetime | None:
        return _optional_timestamp(self.raw, "endTime")

    @property
    def duration(self) -> int | float | None:
        return _optional_number(self.raw, "duration")

    @property
    def distance(self) -> int | float | None:
        return _optional_number(self.raw, "distance")

    @property
    def steps(self) -> int | float | None:
        return _optional_number(self.raw, "steps")

    @property
    def calories(self) -> int | float | None:
        return _optional_number(self.raw, "calories")

    def trackpoints(self) -> Iterator[TrackPoint]:
        values = self.raw.get("trackPoints", [])
        if not isinstance(values, list):
            raise TypeError("Moves activity trackPoints must be an array")
        for index, raw in enumerate(values):
            if not isinstance(raw, dict):
                raise TypeError(f"Moves track point {index} must be an object")
            raw = cast(dict[str, Any], raw)
            yield TrackPoint(
                raw=raw,
                source=SourceRef(
                    archive=self.source.archive,
                    nested_archive=self.source.nested_archive,
                    member=self.source.member,
                    day_index=self.source.day_index,
                    segment_index=self.source.segment_index,
                    activity_index=self.source.activity_index,
                    trackpoint_index=index,
                ),
            )


@dataclass(frozen=True)
class TrackPoint:
    raw: dict[str, Any]
    source: SourceRef

    @property
    def lat(self) -> int | float | None:
        return _optional_number(self.raw, "lat")

    @property
    def lon(self) -> int | float | None:
        return _optional_number(self.raw, "lon")

    @property
    def time(self) -> datetime | None:
        return _optional_timestamp(self.raw, "time")


def inputs() -> Sequence[Path]:
    """Return the configured Moves outer archive."""

    return get_files(config.export_path, guess_compression=False)


def _error(context: str, error: BaseException) -> MovesError:
    return MovesError(f"{context}: {type(error).__name__}: {error}")


def _days_from_archive(archive: Path) -> Iterator[Res[Day]]:
    archive_context = f"Moves archive {archive}"
    try:
        with zipfile.ZipFile(archive, "r") as outer:
            candidates = [name for name in outer.namelist() if name == "json.zip" or name.endswith("/json.zip")]
            if len(candidates) != 1:
                raise MovesError(  # noqa: TRY301
                    f"expected exactly one nested json.zip, found {len(candidates)}"
                )
            nested_name = candidates[0]
            nested_bytes = outer.read(nested_name)
    except Exception as error:
        yield _error(archive_context, error)
        return

    try:
        with zipfile.ZipFile(io.BytesIO(nested_bytes), "r") as nested:
            members = sorted(name for name in nested.namelist() if _DAILY_STORYLINE.fullmatch(name))
            if len(members) == 0:
                raise MovesError("nested json.zip contains no daily storyline members")  # noqa: TRY301
            for member in members:
                member_context = f"{archive_context}, member {nested_name}!/{member}"
                try:
                    value = json.loads(nested.read(member))
                    if not isinstance(value, list):
                        raise TypeError("daily storyline top level must be an array")  # noqa: TRY301
                except Exception as error:
                    yield _error(member_context, error)
                    continue

                for day_index, raw in enumerate(value):
                    if not isinstance(raw, dict):
                        yield MovesError(
                            f"{member_context}, day index {day_index}: daily storyline item must be an object"
                        )
                        continue
                    raw = cast(dict[str, Any], raw)
                    yield Day(
                        raw=raw,
                        source=SourceRef(
                            archive=archive,
                            nested_archive=nested_name,
                            member=member,
                            day_index=day_index,
                        ),
                    )
    except Exception as error:
        yield _error(f"{archive_context}, nested archive {nested_name}", error)


def days() -> Iterator[Res[Day]]:
    """Yield daily storyline records and source-scoped parsing errors."""

    try:
        archives = inputs()
    except Exception as error:
        yield _error("Moves input discovery", error)
        return
    for archive in archives:
        yield from _days_from_archive(Path(archive))


def _children(parents: Iterator[Res[Any]], method: str, label: str) -> Iterator[Res[Any]]:
    for parent in parents:
        if isinstance(parent, Exception):
            yield parent
            continue
        try:
            yield from getattr(parent, method)()
        except Exception as error:
            yield _error(f"Moves {label} at {parent.source}", error)


def segments() -> Iterator[Res[Segment]]:
    """Yield source segments without synthesizing or classifying them."""

    yield from _children(days(), "segments", "day")


def activities() -> Iterator[Res[Activity]]:
    """Yield source activities without synthesizing or classifying them."""

    yield from _children(segments(), "activities", "segment")


def trackpoints() -> Iterator[Res[TrackPoint]]:
    """Yield source track points."""

    yield from _children(activities(), "trackpoints", "activity")


def stats() -> Stats:
    """Return aggregate counts without including source content."""

    counts: Stats = {
        "days": 0,
        "segments": 0,
        "activities": 0,
        "trackpoints": 0,
        "errors": 0,
    }
    for day_result in days():
        if isinstance(day_result, Exception):
            counts["errors"] += 1
            continue
        counts["days"] += 1
        try:
            for segment in day_result.segments():
                counts["segments"] += 1
                try:
                    for activity in segment.activities():
                        counts["activities"] += 1
                        try:
                            for _point in activity.trackpoints():
                                counts["trackpoints"] += 1
                        except Exception:
                            counts["errors"] += 1
                except Exception:
                    counts["errors"] += 1
        except Exception:
            counts["errors"] += 1
    return counts
