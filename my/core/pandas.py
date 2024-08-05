'''
Various pandas helpers and convenience functions
'''
from __future__ import annotations

# todo not sure if belongs to 'core'. It's certainly 'more' core than actual modules, but still not essential
# NOTE: this file is meant to be importable without Pandas installed
import dataclasses
from datetime import datetime, timezone
from pprint import pformat
from typing import TYPE_CHECKING, Any, Iterable, Type, Dict, Literal, Callable, TypeVar

from decorator import decorator

from . import warnings, Res
from .common import LazyLogger, Json, asdict
from .error import error_to_json, extract_error_datetime


logger = LazyLogger(__name__)


if TYPE_CHECKING:
    import pandas as pd

    DataFrameT = pd.DataFrame
    SeriesT = pd.Series
    from pandas._typing import S1  # meh

    FuncT = TypeVar('FuncT', bound=Callable[..., DataFrameT])
    # huh interesting -- with from __future__ import annotations don't even need else clause here?
    # but still if other modules import these we do need some fake runtime types here..
else:
    from typing import Optional

    DataFrameT = Any
    SeriesT = Optional  # just some type with one argument
    S1 = Any


def check_dateish(s: SeriesT[S1]) -> Iterable[str]:
    import pandas as pd  # noqa: F811 not actually a redefinition

    ctype = s.dtype
    if str(ctype).startswith('datetime64'):
        return
    s = s.dropna()
    if len(s) == 0:
        return
    all_timestamps = s.apply(lambda x: isinstance(x, (pd.Timestamp, datetime))).all()
    if not all_timestamps:
        return  # not sure why it would happen, but ok
    tzs = s.map(lambda x: x.tzinfo).drop_duplicates()  # type: ignore[union-attr, var-annotated, arg-type, return-value, unused-ignore]
    examples = s[tzs.index]
    # todo not so sure this warning is that useful... except for stuff without tz
    yield f'''
    All values are timestamp-like, but dtype is not datetime. Most likely, you have mixed timezones:
    {pformat(list(zip(examples, tzs)))}
    '''.strip()


def test_check_dateish() -> None:
    import pandas as pd

    # todo just a dummy test to check it doesn't crash, need something meaningful
    s1 = pd.Series([1, 2, 3])
    list(check_dateish(s1))


# fmt: off
ErrorColPolicy = Literal[
    'add_if_missing',  # add error column if it's missing
    'warn'          ,  # warn, but do not modify
    'ignore'        ,  # no warnings
]
# fmt: on


def check_error_column(df: DataFrameT, *, policy: ErrorColPolicy) -> Iterable[str]:
    if 'error' in df:
        return
    if policy == 'ignore':
        return

    wmsg = '''
No 'error' column detected. You probably forgot to handle errors defensively, which means a single bad entry might bring the whole dataframe down.
'''.strip()
    if policy == 'add_if_missing':
        # todo maybe just add the warnings text as well?
        df['error'] = None
        wmsg += "\nAdding empty 'error' column (see 'error_col_policy' if you want to change this behaviour)"
        pass

    yield wmsg


# TODO ugh. typing this is a mess... perhaps should use .compat.ParamSpec?
@decorator
def check_dataframe(f: FuncT, error_col_policy: ErrorColPolicy = 'add_if_missing', *args, **kwargs) -> DataFrameT:
    df: DataFrameT = f(*args, **kwargs)
    tag = '{f.__module__}:{f.__name__}'
    # makes sense to keep super defensive
    try:
        for col, data in df.reset_index().items():
            for w in check_dateish(data):
                warnings.low(f"{tag}, column '{col}': {w}")
    except Exception as e:
        logger.exception(e)
    try:
        for w in check_error_column(df, policy=error_col_policy):
            warnings.low(f"{tag}, {w}")
    except Exception as e:
        logger.exception(e)
    return df


# todo doctor: could have a suggesion to wrap dataframes with it?? discover by return type?


def error_to_row(e: Exception, *, dt_col: str = 'dt', tz: timezone | None = None) -> Json:
    edt = extract_error_datetime(e)
    if edt is not None and edt.tzinfo is None and tz is not None:
        edt = edt.replace(tzinfo=tz)
    err_dict: Json = error_to_json(e)
    err_dict[dt_col] = edt
    return err_dict


# todo not sure about naming
def to_jsons(it: Iterable[Res[Any]]) -> Iterable[Json]:
    for r in it:
        if isinstance(r, Exception):
            yield error_to_row(r)
        else:
            yield asdict(r)


# mm. https://github.com/python/mypy/issues/8564
# no type for dataclass?
Schema = Any


def _as_columns(s: Schema) -> Dict[str, Type]:
    # todo would be nice to extract properties; add tests for this as well
    if dataclasses.is_dataclass(s):
        return {f.name: f.type for f in dataclasses.fields(s)}
    # else must be NamedTuple??
    # todo assert my.core.common.is_namedtuple?
    return getattr(s, '_field_types')


# todo add proper types
@check_dataframe
def as_dataframe(it: Iterable[Res[Any]], schema: Schema | None = None) -> DataFrameT:
    # todo warn if schema isn't specified?
    # ok nice supports dataframe/NT natively
    # https://github.com/pandas-dev/pandas/pull/27999
    #    but it dispatches dataclass based on the first entry...
    #    https://github.com/pandas-dev/pandas/blob/fc9fdba6592bdb5d0d1147ce4d65639acd897565/pandas/core/frame.py#L562
    # same for NamedTuple -- seems that it takes whatever schema the first NT has
    # so we need to convert each individually... sigh
    import pandas as pd  # noqa: F811 not actually a redefinition

    columns = None if schema is None else list(_as_columns(schema).keys())
    return pd.DataFrame(to_jsons(it), columns=columns)


# ugh. in principle this could be inside the test
# might be due to use of from __future__ import annotations
# can quickly reproduce by running pytest tests/tz.py tests/core/test_pandas.py
# possibly will be resolved after fix in pytest?
# see https://github.com/pytest-dev/pytest/issues/7856
@dataclasses.dataclass
class _X:
    x: int


def test_as_dataframe() -> None:
    import pytest

    it = (dict(i=i, s=f'str{i}') for i in range(10))
    with pytest.warns(UserWarning, match=r"No 'error' column") as record_warnings:  # noqa: F841
        df: DataFrameT = as_dataframe(it)
        # todo test other error col policies
    assert list(df.columns) == ['i', 's', 'error']

    assert len(as_dataframe([])) == 0

    # makes sense to specify the schema so the downstream program doesn't fail in case of empty iterable
    df2: DataFrameT = as_dataframe([], schema=_X)
    assert list(df2.columns) == ['x', 'error']
