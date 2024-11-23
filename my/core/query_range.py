"""
An extension of the my.core.query.select function, allowing you to specify
a type or key to filter the range by -- this creates a filter function
given those values, coercing values on the iterable, returning you a
filtered iterator

See the select_range function below
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from functools import cache
from typing import Any, Callable, NamedTuple

import more_itertools

from .compat import fromisoformat
from .query import (
    ET,
    OrderFunc,
    QueryException,
    Where,
    _handle_generate_order_by,
    select,
)

timedelta_regex = re.compile(
    r"^((?P<weeks>[\.\d]+?)w)?((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$"
)


# https://stackoverflow.com/a/51916936
def parse_timedelta_string(timedelta_str: str) -> timedelta:
    """
    This uses a syntax similar to the 'GNU sleep' command
    e.g.: 1w5d5h10m50s means '1 week, 5 days, 5 hours, 10 minutes, 50 seconds'
    """
    parts = timedelta_regex.match(timedelta_str)
    if parts is None:
        raise ValueError(f"Could not parse time duration from {timedelta_str}.\nValid examples: '8h', '1w2d8h5m20s', '2m4s'")
    time_params = {name: float(param) for name, param in parts.groupdict().items() if param}
    return timedelta(**time_params)


def parse_timedelta_float(timedelta_str: str) -> float:
    return parse_timedelta_string(timedelta_str).total_seconds()


def parse_datetime_float(date_str: str) -> float:
    """
    parses multiple possible representations of a datetime
    into a float, else raises a QueryException

    the query_cli interface compares floats instead of timestamps
    when comparing datetimes since handling it is unknown
    whether the sources the user is selecting from is tz-aware
    or not (or perhaps a mix of both?)
    """
    ds = date_str.strip()
    # special case
    if ds == "now":
        return time.time()
    # epoch timestamp
    try:
        # also handles epoch timestamps as integers
        ds_float = float(ds)
        # convert to make sure its a valid datetime
        datetime.fromtimestamp(ds_float)
    except ValueError:
        pass
    else:
        return ds_float
    try:
        # isoformat - default format when you call str() on datetime
        # this also parses dates like '2020-01-01'
        return datetime.fromisoformat(ds).timestamp()
    except ValueError:
        pass
    try:
        return fromisoformat(ds).timestamp()
    except (AssertionError, ValueError):
        pass

    try:
        import dateparser
    except ImportError:
        pass
    else:
        # dateparser is a bit more lenient than the above, lets you type
        # all sorts of dates as inputs
        # https://github.com/scrapinghub/dateparser#how-to-use
        res: datetime | None = dateparser.parse(ds, settings={"DATE_ORDER": "YMD"})
        if res is not None:
            return res.timestamp()

    raise QueryException(f"Was not able to parse {ds} into a datetime")


# probably DateLike input? but a user could specify an order_key
# which is an epoch timestamp or a float value which they
# expect to be converted to a datetime to compare
@cache
def _datelike_to_float(dl: Any) -> float:
    if isinstance(dl, datetime):
        return dl.timestamp()
    elif isinstance(dl, date):
        # hmm... sets the hours/minutes/seconds to 0 -- make this configurable?
        return (datetime.combine(dl, datetime.min.time())).timestamp()
    else:
        try:
            return parse_datetime_float(dl)
        except QueryException as q:
            raise QueryException(f"While attempting to extract datetime from {dl}, to order by datetime:\n\n" + str(q))  # noqa: B904


class RangeTuple(NamedTuple):
    """Can specify 0, 1 or 2 non-none items in a range -- but not all 3

    As an example, using datetimes/timedelta (some date, and possibly a duration)

    where 1 arg is not None
        - after is not None: filters it to any items 'after' the datetime
        - before is not None: filters to any items 'before' the datetime
        - within: filters to any items 'within' the timedelta, assuming you meant within the current
            timeframe, so before = time.time()

    when 2 args are not None:
        - after and within, filters anything after the initial 'after' time
            but 'within' the timeframe (parsed timedelta, e.g. 5d)
        - before and within, anything 'within' the timeframe, starting at the end
            of the timeframe -- 'before'
        - before and after - anything after 'after' and before 'before', acts as a time range
    """

    # technically doesn't need to be Optional[Any],
    # just to make it more clear these can be None
    after: Any | None
    before: Any | None
    within: Any | None


Converter = Callable[[Any], Any]


def _parse_range(
    *,
    unparsed_range: RangeTuple,
    end_parser: Converter,
    within_parser: Converter,
    parsed_range: RangeTuple | None = None,
    error_message: str | None = None,
) -> RangeTuple | None:

    if parsed_range is not None:
        return parsed_range

    err_msg = error_message or RangeTuple.__doc__
    assert err_msg is not None  # make mypy happy
    after, before, within = None, None, None

    none_count = more_itertools.ilen(filter(lambda o: o is None, list(unparsed_range)))
    if none_count == 3:
        return None
    if none_count == 0:
        raise QueryException("Cannot specify 'after', 'before' and 'within' at the same time!\n\n" + err_msg)

    [after_str, before_str, within_str] = tuple(unparsed_range)
    after = end_parser(after_str) if after_str is not None else None
    before = end_parser(before_str) if before_str is not None else None
    within = within_parser(within_str) if within_str is not None else None

    return RangeTuple(after=after, before=before, within=within)


def _create_range_filter(
    *,
    unparsed_range: RangeTuple,
    end_parser: Converter,
    within_parser: Converter,
    attr_func: Where,
    parsed_range: RangeTuple | None = None,
    default_before: Any | None = None,
    value_coercion_func: Converter | None = None,
    error_message: str | None = None,
) -> Where | None:
    """
    Handles:
        - parsing the user input into values that are comparable to items the iterable returns
            - unparsed_range: tuple of raw values from user
            - end_parser: parses 'before' and 'after' (e.g. start/end dates)
            - within_parser: parser for the 'range' (e.g. timedelta)
            - error_message: allow overriding the default error message while parsing
        - converting items from the iterable to some coerced value, so that its comparable to
          the before, after and within parts of the range
            - if value_coercion_func is present, tries to use that
              to convert the value returned by the attr_func

    unparsed_range is a tuple of the input data from the user

    parsed_range can be passed if you've already parsed unparsed_range

    'default_before' specifies what to set if no before or after was specified in
    RangeTuple and we need an endpoint to end the range at. For example, if you wanted
    data from an iterable from the last week, you could specify default_before to be now (time.time()),
    and unparsed_range.within to be 7 days

    Creates a predicate that checks if some item from the iterator is
    within some range. this is typically used for datelike input, but the user could
    specify an integer or float item to order the values by/in some timeframe

    It requires the value you're comparing by to support comparable/addition operators (=, <, >, +, -)

    attr_func is a function which accepts the object from the iterator and returns
    the value to compare the range boundaries to. typically generated by _generate_order_by_func

    To force the values you're sorting by to be in some specified type,
    this allows a 'value_coercion_func', which optionally converts the value
    returned by attr_func to some shared type (see _datelike_to_float for an example)
    """

    rn = _parse_range(unparsed_range=unparsed_range,
                      end_parser=end_parser,
                      within_parser=within_parser,
                      parsed_range=parsed_range,
                      error_message=error_message)

    # user specified all 'None' items in the range, don't need to filter
    if rn is None:
        return None

    after = rn.after
    before = rn.before
    within = rn.within

    # hmm... not sure how to correctly manage
    # inclusivity here? Is [after, before) currently,
    # items are included on the lower bound but not the
    # upper bound
    # typically used for datetimes so doesn't have to
    # be exact in that case
    def generated_predicate(obj: Any) -> bool:
        ov: Any = attr_func(obj)
        if value_coercion_func is not None:
            ov = value_coercion_func(ov)
        if after is not None:
            if before is not None:
                # squeeze between before/after
                return ov >= after and ov < before
            elif within is not None:
                # after some start point + some range
                allow_before = after + within
                return ov >= after and ov < allow_before
            else:
                return ov >= after
        elif before is not None:
            if within is not None:
                allow_after = before - within
                # before a startpoint + some range
                return ov >= allow_after and ov < before
            else:
                # just before the startpoint
                return ov < before
        else:
            # only specified within, default before to now
            if default_before is None:
                raise QueryException("Only received a range length, with no start or end point to compare against")
            allow_after = default_before - within
            return ov >= allow_after and ov < default_before

    return generated_predicate


# main interface to this file from my.core.__main__.py
def select_range(
    itr: Iterator[ET],
    *,
    where: Where | None = None,
    order_key: str | None = None,
    order_value: Where | None = None,
    order_by_value_type: type | None = None,
    unparsed_range: RangeTuple | None = None,
    reverse: bool = False,
    limit: int | None = None,
    drop_unsorted: bool = False,
    wrap_unsorted: bool = False,
    warn_exceptions: bool = False,
    warn_func: Callable[[Exception], None] | None = None,
    drop_exceptions: bool = False,
    raise_exceptions: bool = False,
) -> Iterator[ET]:
    """
    A specialized select function which offers generating functions
    to filter/query ranges from an iterable

    order_key and order_value are used in the same way they are in select

    If you specify order_by_value_type, it tries to search for an attribute
    on each object/type which has that type, ordering the iterable by that value

    unparsed_range is a tuple of length 3, specifying 'after', 'before', 'duration',
    i.e. some start point to allow the computed value we're ordering by, some
    end point and a duration (can use the RangeTuple NamedTuple to construct one)

    (this is typically parsed/created in my.core.__main__, from CLI flags

    If you specify a range, drop_unsorted is forced to be True
    """

    # if the user specified a range with no data, set the unparsed_range to None
    if unparsed_range == RangeTuple(None, None, None):
        unparsed_range = None

    # some operations to do before ordering/filtering
    if drop_exceptions or raise_exceptions or where is not None or warn_exceptions:
        # doesn't wrap unsortable items, because we pass no order related kwargs
        itr = select(
            itr,
            where=where,
            drop_exceptions=drop_exceptions,
            raise_exceptions=raise_exceptions,
            warn_exceptions=warn_exceptions,
            warn_func=warn_func,
        )

    order_by_chosen: OrderFunc | None = None

    # if the user didn't specify an attribute to order value, but specified a type
    # we should search for on each value in the iterator
    if order_value is None and order_by_value_type is not None:
        # search for that type on the iterator object
        order_value = lambda o: isinstance(o, order_by_value_type)

    # if the user supplied a order_key, and/or we've generated an order_value, create
    # the function that accesses that type on each value in the iterator
    if order_key is not None or order_value is not None:
        # _generate_order_value_func internally here creates a copy of the iterator, which has to
        # be consumed in-case we're sorting by mixed types
        order_by_chosen, itr = _handle_generate_order_by(itr, order_key=order_key, order_value=order_value)
        # signifies that itr is empty -- can early return here
        if order_by_chosen is None:
            return itr

    # test if the user is trying to specify a range to filter the items by
    if unparsed_range is not None:

        if order_by_chosen is None:
            raise QueryException("""Can't order by range if we have no way to order_by!
Specify a type or a key to order the value by""")

        # force drop_unsorted=True so we can use _create_range_filter
        # sort the iterable by the generated order_by_chosen function
        itr = select(itr, order_by=order_by_chosen, drop_unsorted=True)
        filter_func: Where | None
        if order_by_value_type in [datetime, date]:
            filter_func = _create_range_filter(
                unparsed_range=unparsed_range,
                end_parser=parse_datetime_float,
                within_parser=parse_timedelta_float,
                attr_func=order_by_chosen,  # type: ignore[arg-type]
                default_before=time.time(),
                value_coercion_func=_datelike_to_float,
            )
        elif order_by_value_type in [int, float]:
            # allow primitives to be converted using the default int(), float() callables
            filter_func = _create_range_filter(
                unparsed_range=unparsed_range,
                end_parser=order_by_value_type,
                within_parser=order_by_value_type,
                attr_func=order_by_chosen,  # type: ignore[arg-type]
                default_before=None,
                value_coercion_func=order_by_value_type,
            )
        else:
            # TODO: add additional kwargs to let the user sort by other values, by specifying the parsers?
            # would need to allow passing the end_parser, within parser, default before and value_coercion_func...
            # (seems like a lot?)
            raise QueryException("Sorting by custom types is currently unsupported")

        # use the created filter function
        # we've already applied drop_exceptions and kwargs related to unsortable values above
        itr = select(itr, where=filter_func, limit=limit, reverse=reverse)
    else:
        # wrap_unsorted may be used here if the user specified an order_key,
        # or manually passed a order_value function
        #
        # this select is also run if the user didn't specify anything to
        # order by, and is just returning the data in the same order as
        # as the source iterable
        # i.e. none of the range-related filtering code ran, this is just a select
        itr = select(itr,
                     order_by=order_by_chosen,
                     wrap_unsorted=wrap_unsorted,
                     drop_unsorted=drop_unsorted,
                     limit=limit,
                     reverse=reverse)
    return itr


# reuse items from query for testing
from .query import _A, _B, _Float, _mixed_iter_errors


def test_filter_in_timeframe() -> None:

    from itertools import chain

    jan_1_2005 = datetime(year=2005, month=1, day=1, hour=1, minute=1, second=1)
    jan_1_2016 = datetime(year=2016, month=1, day=1, hour=1, minute=1, second=1)

    rng = RangeTuple(after=str(jan_1_2005), before=str(jan_1_2016), within=None)

    # items between 2005 and 2016
    res = list(select_range(_mixed_iter_errors(), order_by_value_type=datetime, unparsed_range=rng, drop_exceptions=True))

    assert res == [_A(x=datetime(2005, 4, 10, 4, 10, 1), y=2, z=-5),
                   _A(x=datetime(2005, 5, 10, 4, 10, 1), y=10, z=2),
                   _A(x=datetime(2009, 3, 10, 4, 10, 1), y=12, z=1),
                   _A(x=datetime(2009, 5, 10, 4, 10, 1), y=5, z=10),
                   _B(y=datetime(year=2015, month=5, day=10, hour=4, minute=10, second=1))]

    rng = RangeTuple(before=str(jan_1_2016), within="52w", after=None)

    # from 2016, going back 52 weeks (about a year?)
    res = list(select_range(_mixed_iter_errors(), order_by_value_type=datetime, unparsed_range=rng, drop_exceptions=True))

    assert res == [_B(y=datetime(year=2015, month=5, day=10, hour=4, minute=10, second=1))]

    # test passing just a within while using a datetime. should default to using current time
    recent_time = datetime.now() - timedelta(days=5)
    obj = _A(x=recent_time, y=2, z=-5)

    rng = RangeTuple(before=None, after=None, within="1w")
    res = list(select_range(chain(_mixed_iter_errors(), iter([obj])),
                            order_by_value_type=datetime,
                            unparsed_range=rng, drop_exceptions=True))

    assert res == [obj]

    # dont pass any range related stuff, use where/drop_exceptions and the limit flag
    # to make sure this falls through properly to using select kwargs

    using_range = list(select_range(_mixed_iter_errors(), drop_exceptions=True, limit=5))
    normal = list(select(_mixed_iter_errors(), limit=5, where=lambda o: not isinstance(o, Exception)))

    assert using_range == normal


def test_query_range_float_value_type() -> None:

    def floaty_iter() -> Iterator[_Float]:
        for v in range(1, 6):
            yield _Float(float(v + 0.5))

    rng = RangeTuple(after=2, before=6.1, within=None)
    res = list(select_range(floaty_iter(), order_by_value_type=float, unparsed_range=rng, drop_exceptions=True))
    assert res == [_Float(2.5), _Float(3.5), _Float(4.5), _Float(5.5)]


def test_range_predicate() -> None:

    from functools import partial

    def src() -> Iterator[str]:
        yield from map(str, range(15))

    identity = lambda o: o

    # convert any float values to ints
    coerce_int_parser = lambda o: int(float(o))
    int_filter_func = partial(
        _create_range_filter,
        attr_func=identity,
        end_parser=coerce_int_parser,
        within_parser=coerce_int_parser,
        value_coercion_func=coerce_int_parser,
    )

    # filter from 0 to 5
    rn: RangeTuple = RangeTuple("0", "5", None)
    zero_to_five_filter: Where | None = int_filter_func(unparsed_range=rn)
    assert zero_to_five_filter is not None
    # this is just a Where function, given some input it return True/False if the value is allowed
    assert zero_to_five_filter(3) is True
    assert zero_to_five_filter(10) is False

    # this is expected, range_predicate is not inclusive on the far end
    assert list(filter(zero_to_five_filter, src())) == ["0", "1", "2", "3", "4"]

    # items less than 3, going 3.5 (converted to 3 by the coerce_int_parser) down
    rn = RangeTuple(None, 3, "3.5")
    assert list(filter(int_filter_func(unparsed_range=rn, attr_func=identity), src())) == ["0", "1", "2"]


def test_parse_range() -> None:

    from functools import partial

    import pytest

    rn = RangeTuple("0", "5", None)
    res = _parse_range(unparsed_range=rn, end_parser=int, within_parser=int)

    assert res == RangeTuple(after=0, before=5, within=None)

    dt_parse_range = partial(_parse_range, end_parser=parse_datetime_float, within_parser=parse_timedelta_float)

    start_date = datetime.now()
    end_date = start_date + timedelta(seconds=60)

    # convert start items to strings, which need to be parsed back
    rn = RangeTuple(str(start_date), str(end_date.timestamp()), None)
    res2 = dt_parse_range(unparsed_range=rn)

    assert res2 == RangeTuple(after=start_date.timestamp(), before=end_date.timestamp(), within=None)

    # can't specify all three
    with pytest.raises(QueryException, match=r"Cannot specify 'after', 'before' and 'within'"):
        dt_parse_range(unparsed_range=RangeTuple(str(start_date), str(end_date.timestamp()), "7d"))

    # if you specify noting, should return None
    res3 = dt_parse_range(unparsed_range=RangeTuple(None, None, None))
    assert res3 is None


def test_parse_timedelta_string() -> None:

    import pytest

    with pytest.raises(ValueError, match=r"Could not parse time duration from"):
        parse_timedelta_string("5xxx")

    res = parse_timedelta_string("1w5d5h10m50s")
    assert res == timedelta(days=7.0 + 5.0, hours=5.0, minutes=10.0, seconds=50.0)


def test_parse_datetime_float() -> None:
    pnow = parse_datetime_float("now")
    sec_diff = abs(pnow - datetime.now().timestamp())
    # should probably never fail? could mock time.time
    # but there seems to be issues with doing that use C-libraries (as time.time) does
    # https://docs.python.org/3/library/unittest.mock-examples.html#partial-mocking
    assert sec_diff < 60

    dt = datetime.now()
    dt_float_s = str(dt.timestamp())
    dt_int_s = str(int(dt.timestamp()))

    # float/int representations as strings
    assert dt.timestamp() == parse_datetime_float(dt_float_s)
    assert int(dt.timestamp()) == int(parse_datetime_float(dt_int_s))

    # test parsing isoformat
    assert dt.timestamp() == parse_datetime_float(str(dt))
