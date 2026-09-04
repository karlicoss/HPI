from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import TYPE_CHECKING, assert_type, get_type_hints

import pytest

from my.core.datetime import AwareDateTime, Date, NaiveDateTime, aware, date_only, naive
from my.core.types import datetime_aware, datetime_naive

from .common import skip_if_uses_optional_deps


# A tzinfo object can exist without providing a UTC offset.
# This checks that aware() requires a usable offset and naive() requires tzinfo to be absent.
class _NoOffset(tzinfo):
    def utcoffset(self, _dt: datetime | None) -> None:
        return None

    def dst(self, _dt: datetime | None) -> None:
        return None

    def tzname(self, _dt: datetime | None) -> None:
        return None


def test_date_only_preserves_value() -> None:
    d = date(2024, 6, 3)
    result = date_only(d)
    assert_type(result, Date)
    assert result is d


@pytest.mark.parametrize('tz', [None, UTC, _NoOffset()])
def test_date_only_rejects_datetime(tz: tzinfo | None) -> None:
    with pytest.raises(AssertionError):
        date_only(datetime(2024, 6, 3, tzinfo=tz))


def test_date_only_explicit_extraction() -> None:
    dt = datetime(2024, 6, 3, 12, tzinfo=UTC)
    result = date_only(dt.date())
    assert_type(result, Date)
    assert result == date(2024, 6, 3)


@pytest.mark.parametrize('tz', [UTC, timezone(timedelta(hours=5, minutes=30))])
def test_aware_preserves_value(tz: tzinfo) -> None:
    dt = datetime(2024, 6, 3, 12, 34, 56, 123456, tzinfo=tz, fold=1)
    result = aware(dt)
    assert_type(result, AwareDateTime)
    assert result is dt


def test_naive_preserves_value() -> None:
    dt = datetime(2024, 6, 3, 12, 34, 56, 123456, fold=1)
    result = naive(dt)
    assert_type(result, NaiveDateTime)
    assert result is dt


@pytest.mark.parametrize('tz', [None, _NoOffset()])
def test_aware_requires_offset(tz: tzinfo | None) -> None:
    with pytest.raises(AssertionError):
        aware(datetime(2024, 6, 3, tzinfo=tz))


@pytest.mark.parametrize('tz', [UTC, _NoOffset()])
def test_naive_requires_absent_timezone(tz: tzinfo) -> None:
    with pytest.raises(AssertionError):
        naive(datetime(2024, 6, 3, tzinfo=tz))


@dataclass
class _Event:
    day: Date
    aware_dt: AwareDateTime
    naive_dt: NaiveDateTime


def test_runtime_annotations() -> None:
    assert get_type_hints(_Event) == {'day': date, 'aware_dt': datetime, 'naive_dt': datetime}
    assert get_type_hints(date_only) == {'d': date, 'return': date}
    assert get_type_hints(aware) == {'dt': datetime, 'return': datetime}
    assert get_type_hints(naive) == {'dt': datetime, 'return': datetime}
    assert datetime_aware is datetime
    assert datetime_naive is datetime


@skip_if_uses_optional_deps
def test_cachew_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cachew import settings

    from my.core.cachew import mcachew

    monkeypatch.setattr(settings, 'ENABLE', True)
    monkeypatch.setattr(settings, 'THROW_ON_ERROR', True)

    event = _Event(
        day=date_only(date(2024, 6, 3)),
        aware_dt=aware(datetime(2024, 6, 3, 12, tzinfo=timezone(timedelta(hours=5, minutes=30)))),
        naive_dt=naive(datetime(2024, 6, 3, 12)),
    )
    calls = 0

    @mcachew(cache_path=tmp_path / 'datetimes')
    def events() -> Iterator[_Event]:
        nonlocal calls
        calls += 1
        yield event

    assert list(events()) == [event]
    [restored] = events()
    assert calls == 1
    assert restored == event
    assert type(restored.day) is date
    assert restored.aware_dt.utcoffset() == event.aware_dt.utcoffset()
    assert restored.naive_dt.tzinfo is None


if TYPE_CHECKING:

    def _test_static_assignability(
        *, d: date, day: Date, dt: datetime, aware_dt: AwareDateTime, naive_dt: NaiveDateTime
    ) -> None:
        _plain_date: date = day
        _plain_aware: datetime = aware_dt
        _plain_naive: datetime = naive_dt

        # These ignores must remain necessary so unchecked and differently branded values cannot be assigned.
        _unchecked_date: Date = d  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _datetime_as_date: Date = dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _aware_as_date: Date = aware_dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _naive_as_date: Date = naive_dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _date_as_datetime: datetime = day  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _unchecked_aware: AwareDateTime = dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _unchecked_naive: NaiveDateTime = dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _wrong_aware: AwareDateTime = naive_dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        _wrong_naive: NaiveDateTime = aware_dt  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
