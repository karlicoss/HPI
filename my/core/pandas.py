'''
Various pandas helpers and convenience functions
'''
# todo not sure if belongs to 'core'. It's certainly 'more' core than actual modules, but still not essential
# NOTE: this file is meant to be importable without Pandas installed
from datetime import datetime
from pprint import pformat
from typing import Optional, TYPE_CHECKING, Any, Iterable
from . import warnings
from .common import LazyLogger

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


import traceback
from typing import Dict, Any
from .error import extract_error_datetime
def error_to_row(e: Exception, *, dt_col: str='dt', tz=None) -> Dict[str, Any]:
    edt = extract_error_datetime(e)
    if edt is not None and edt.tzinfo is None and tz is not None:
        edt = edt.replace(tzinfo=tz)
    estr = ''.join(traceback.format_exception(Exception, e, e.__traceback__))
    return {
        'error': estr,
        dt_col : edt,
    }
