'''
Various pandas helpers and convenience functions
'''
# todo not sure if belongs to 'core'. It's certainly 'more' core than actual modules, but still not essential
# NOTE: this file is meant to be importable without Pandas installed
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
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


def check_dateish(s) -> Optional[str]:
    import pandas as pd # type: ignore
    ctype = s.dtype
    if str(ctype).startswith('datetime64'):
        return None
    s = s.dropna()
    if len(s) == 0:
        return None
    all_timestamps = s.apply(lambda x: isinstance(x, (pd.Timestamp, datetime))).all()
    if all_timestamps:
        return 'All values are timestamp-like, but dtype is not datetime. Most likely, you have mixed timezones'
    return None


from typing import Any, Callable, TypeVar
FuncT = TypeVar('FuncT', bound=Callable[..., DataFrameT])

def check_dataframe(f: FuncT) -> FuncT:
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs) -> DataFrameT:
        df = f(*args, **kwargs)
        # todo make super defensive?
        for col, data in df.reset_index().iteritems():
            res = check_dateish(data)
            if res is not None:
                warnings.low(f"{f.__module__}:{f.__name__}, column '{col}': {res}")
        return df
    # https://github.com/python/mypy/issues/1927
    return wrapper # type: ignore[return-value]

# todo doctor: could have a suggesion to wrap dataframes with it?? discover by return type?
