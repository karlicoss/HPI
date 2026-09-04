"""
Checked date and datetime annotations for parser and API boundaries.

Inspired by Glyph's DateType library: https://github.com/glyph/DateType
The distinct date/datetime types and checked boundary helpers follow its design, using lightweight NewTypes here.

AwareDateTime and NaiveDateTime are distinct static types, unlike the documentation aliases in my.core.types.
Date describes a date that is not a datetime, despite datetime inheriting from date in the standard library.
At runtime Date aliases date and both datetime types alias datetime, preserving compatibility with introspection and cachew.
Use date_only(), aware(), and naive() to validate existing values without transforming or copying them.
Use the type names only in annotations, not as constructors or runtime validation checks.

These types do not track awareness through every datetime operation.
For example, replace(tzinfo=None) can retain the static AwareDateTime type even though its result is naive.
Runtime introspection cannot distinguish these checked types from their stdlib bases or enforce their invariants when loading cached values.

We may eventually use DateType itself for more precise typing of date and datetime operations.
The public names deliberately match that library to ease migration, though stdlib datetime APIs may need explicit adapters.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, NewType, cast

__all__ = ['AwareDateTime', 'Date', 'NaiveDateTime', 'aware', 'date_only', 'naive']


if TYPE_CHECKING:
    # NewType values are accepted as their stdlib bases, but unchecked values cannot be assigned to these NewTypes.
    # Use date_only(), aware(), or naive() to validate a value before assigning the corresponding type.
    Date = NewType('Date', date)
    AwareDateTime = NewType('AwareDateTime', datetime)
    NaiveDateTime = NewType('NaiveDateTime', datetime)
else:
    Date = date
    AwareDateTime = datetime
    NaiveDateTime = datetime


def date_only(d: date) -> Date:
    """
    Check that d is a date rather than a datetime and return it unchanged.

    To deliberately extract a date from a datetime, use date_only(dt.date()).
    """
    assert not isinstance(d, datetime), d
    return cast(Date, d)


def aware(dt: datetime) -> AwareDateTime:
    """
    Check that dt has a UTC offset and return it unchanged.

    See https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """
    assert dt.utcoffset() is not None, dt
    return cast(AwareDateTime, dt)


def naive(dt: datetime) -> NaiveDateTime:
    """Check that dt has no timezone information and return it unchanged."""
    # Intentionally stricter than Python's definition, which also permits tzinfo returning no UTC offset.
    # Requiring absent tzinfo matches datetype.naive() and pytz.localize().
    # A datetime with tzinfo but no UTC offset is rejected by both aware() and naive().
    assert dt.tzinfo is None, dt
    return cast(NaiveDateTime, dt)
