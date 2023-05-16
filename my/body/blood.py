"""
Blood tracking (manual org-mode entries)
"""

from datetime import datetime
from typing import Iterable, NamedTuple, Optional

from ..core.error import Res
from ..core.orgmode import parse_org_datetime, one_table


import pandas as pd
import orgparse


from my.config import blood as config  # type: ignore[attr-defined]


class Entry(NamedTuple):
    dt: datetime

    ketones      : Optional[float]=None
    glucose      : Optional[float]=None

    vitamin_d    : Optional[float]=None
    vitamin_b12  : Optional[float]=None

    hdl          : Optional[float]=None
    ldl          : Optional[float]=None
    triglycerides: Optional[float]=None

    source       : Optional[str]=None
    extra        : Optional[str]=None


Result = Res[Entry]


def try_float(s: str) -> Optional[float]:
    l = s.split()
    if len(l) == 0:
        return None
    # meh. this is to strip away HI/LO? Maybe need extract_float instead or something
    x = l[0].strip()
    if len(x) == 0:
        return None
    return float(x)


def glucose_ketones_data() -> Iterable[Result]:
    o = orgparse.load(config.blood_log)
    [n] = [x for x in o if x.heading == 'glucose/ketones']
    tbl = one_table(n)
    # todo some sort of sql-like interface for org tables might be ideal?
    for l in tbl.as_dicts:
        kets = l['ket']
        glus = l['glu']
        extra = l['notes']
        dt = parse_org_datetime(l['datetime'])
        try:
            assert isinstance(dt, datetime)
            ket = try_float(kets)
            glu = try_float(glus)
        except Exception as e:
            ex = RuntimeError(f'While parsing {l}')
            ex.__cause__ = e
            yield ex
        else:
            yield Entry(
                dt=dt,
                ketones=ket,
                glucose=glu,
                extra=extra,
            )


def blood_tests_data() -> Iterable[Result]:
    o = orgparse.load(config.blood_log)
    [n] = [x for x in o if x.heading == 'blood tests']
    tbl = one_table(n)
    for d in tbl.as_dicts:
        try:
            dt = parse_org_datetime(d['datetime'])
            assert isinstance(dt, datetime), dt

            F = lambda n: try_float(d[n])
            yield Entry(
                dt=dt,

                vitamin_d    =F('VD nm/L'),
                vitamin_b12  =F('B12 pm/L'),

                hdl          =F('HDL mm/L'),
                ldl          =F('LDL mm/L'),
                triglycerides=F('Trig mm/L'),

                source       =d['source'],
                extra        =d['notes'],
            )
        except Exception as e:
            ex = RuntimeError(f'While parsing {d}')
            ex.__cause__ = e
            yield ex


def data() -> Iterable[Result]:
    from itertools import chain
    from ..core.error import sort_res_by
    datas = chain(glucose_ketones_data(), blood_tests_data())
    return sort_res_by(datas, key=lambda e: e.dt)


def dataframe() -> pd.DataFrame:
    rows = []
    for x in data():
        if isinstance(x, Exception):
            # todo use some core helper? this is a pretty common operation
            d = {'error': str(x)}
        else:
            d = x._asdict()
        rows.append(d)
    return pd.DataFrame(rows)


def stats():
    from ..core import stat
    return stat(data)


def test():
    print(dataframe())
    assert len(dataframe()) > 10
