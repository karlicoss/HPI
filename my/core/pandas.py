'''
Various pandas helpers and convenience functions
'''
# todo not sure if belongs to 'core'. It's certainly 'more' core than actual modules, but still not essential
# NOTE: this file is meant to be importable without Pandas installed
from datetime import datetime
from pprint import pformat
from typing import Optional, TYPE_CHECKING, Any, Iterable
from . import warnings


if TYPE_CHECKING:
    # this is kinda pointless at the moment, but handy to annotate DF returning methods now
    # later will be unignored when they implement type annotations
    import pandas as pd # type: ignore
    # DataFrameT = pd.DataFrame
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


from typing import Any, Callable, TypeVar
FuncT = TypeVar('FuncT', bound=Callable[..., DataFrameT])

def check_dataframe(f: FuncT) -> FuncT:
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs) -> DataFrameT:
        df = f(*args, **kwargs)
        # todo make super defensive?
        for col, data in df.reset_index().iteritems():
            for w in check_dateish(data):
                warnings.low(f"{f.__module__}:{f.__name__}, column '{col}': {w}")
        return df
    # https://github.com/python/mypy/issues/1927
    return wrapper # type: ignore[return-value]

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
