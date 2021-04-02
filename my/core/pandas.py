'''
Various pandas helpers and convenience functions
'''
# todo not sure if belongs to 'core'. It's certainly 'more' core than actual modules, but still not essential
# NOTE: this file is meant to be importable without Pandas installed
from datetime import datetime
from pprint import pformat
from typing import Optional, TYPE_CHECKING, Any, Iterable, Type, Dict
from . import warnings, Res
from .common import LazyLogger, Json, asdict

logger = LazyLogger(__name__)


if TYPE_CHECKING:
    # this is kinda pointless at the moment, but handy to annotate DF returning methods now
    # later will be unignored when they implement type annotations
    import pandas as pd # type: ignore
    # DataFrameT = pd.DataFrame
    # TODO ugh. pretty annoying, having any is not very useful since it would allow arbitrary coercions..
    # ideally want to use a type that's like Any but doesn't allow arbitrary coercions??
    DataFrameT = Any
else:
    # in runtime, make it defensive so it works without pandas
    DataFrameT = Any


def check_dateish(s) -> Iterable[str]:
    import pandas as pd # type: ignore
    ctype = s.dtype
    if str(ctype).startswith('datetime64'):
        return
    s = s.dropna()
    if len(s) == 0:
        return
    all_timestamps = s.apply(lambda x: isinstance(x, (pd.Timestamp, datetime))).all()
    if not all_timestamps:
        return # not sure why it would happen, but ok
    tzs = s.map(lambda x: x.tzinfo).drop_duplicates()
    examples = s[tzs.index]
    # todo not so sure this warning is that useful... except for stuff without tz
    yield f'''
    All values are timestamp-like, but dtype is not datetime. Most likely, you have mixed timezones:
    {pformat(list(zip(examples, tzs)))}
    '''.strip()


from .compat import Literal

ErrorColPolicy = Literal[
    'add_if_missing', # add error column if it's missing
    'warn'          , # warn, but do not modify
    'ignore'        , # no warnings
]

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


from typing import Any, Callable, TypeVar
FuncT = TypeVar('FuncT', bound=Callable[..., DataFrameT])

# TODO ugh. typing this is a mess... shoul I use mypy_extensions.VarArg/KwArgs?? or what??
from decorator import decorator
@decorator
def check_dataframe(f: FuncT, error_col_policy: ErrorColPolicy='add_if_missing', *args, **kwargs) -> DataFrameT:
    df = f(*args, **kwargs)
    tag = '{f.__module__}:{f.__name__}'
    # makes sense to keep super defensive
    try:
        for col, data in df.reset_index().iteritems():
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


def error_to_row(e: Exception, *, dt_col: str='dt', tz=None) -> Json:
    from .error import error_to_json, extract_error_datetime
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
    import dataclasses as D
    if D.is_dataclass(s):
        return {f.name: f.type for f in D.fields(s)}
    # else must be NamedTuple??
    # todo assert my.core.common.is_namedtuple?
    return getattr(s, '_field_types')


# todo add proper types
@check_dataframe
def as_dataframe(it: Iterable[Res[Any]], schema: Optional[Schema]=None) -> DataFrameT:
    # todo warn if schema isn't specified?
    # ok nice supports dataframe/NT natively
    # https://github.com/pandas-dev/pandas/pull/27999
    #    but it dispatches dataclass based on the first entry...
    #    https://github.com/pandas-dev/pandas/blob/fc9fdba6592bdb5d0d1147ce4d65639acd897565/pandas/core/frame.py#L562
    # same for NamedTuple -- seems that it takes whatever schema the first NT has
    # so we need to convert each individually... sigh
    import pandas as pd
    columns = None if schema is None else list(_as_columns(schema).keys())
    return pd.DataFrame(to_jsons(it), columns=columns)


def test_as_dataframe() -> None:
    import pytest
    it = (dict(i=i, s=f'str{i}') for i in range(10))
    with pytest.warns(UserWarning, match=r"No 'error' column") as record_warnings:
        df = as_dataframe(it)
        # todo test other error col policies
    assert list(df.columns) == ['i', 's', 'error']

    assert len(as_dataframe([])) == 0

    from dataclasses import dataclass
    @dataclass
    class X:
        x: int

    # makes sense to specify the schema so the downstream program doesn't fail in case of empty iterable
    df = as_dataframe([], schema=X)
    assert list(df.columns) == ['x', 'error']
