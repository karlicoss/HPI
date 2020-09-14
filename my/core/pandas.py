'''
Various pandas helpers and convenience functions
'''
# todo not sure if belongs to 'core'. It's certainly 'more' core than actual modules, but still not essential
from typing import Optional
import warnings


# FIXME need to make sure check_dataframe decorator can be used without actually importing pandas
# so need to move this import drom top level
import pandas as pd # type: ignore

# todo special warning type?


def check_dateish(s) -> Optional[str]:
    ctype = s.dtype
    if str(ctype).startswith('datetime64'):
        return None
    s = s.dropna()
    if len(s) == 0:
        return None
    all_timestamps = s.apply(lambda x: isinstance(x, pd.Timestamp)).all()
    if all_timestamps:
        return 'All values are pd.Timestamp, but dtype is not datetime. Most likely, you have mixed timezones'
    return None


def check_dataframe(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs) -> pd.DataFrame:
        df = f(*args, **kwargs)
        # todo make super defensive?
        # TODO check index as well?
        for col, data in df.iteritems():
            res = check_dateish(data)
            if res is not None:
                warnings.warn(f"{f.__name__}, column '{col}': {res}")
        return df
    return wrapper

# todo doctor: could have a suggesion to wrap dataframes with it?? discover by return type?
