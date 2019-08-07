#!/usr/bin/env python3
from datetime import datetime
from typing import Iterable, NamedTuple, Optional

import porg
from kython import listify
from kython.org import parse_org_date

from ..paths import LOGS


blood_log = LOGS / 'blood.org'

class Entry(NamedTuple):
    dt: datetime
    ket: Optional[float]
    glu: Optional[float]
    extra: str


def iter_data() -> Iterable[Entry]:
    o = porg.Org.from_file(blood_log)
    tbl = o.xpath('//table')
    for l in tbl.lines:
        kets = l['ket'].strip()
        glus = l['glu'].strip()
        extra = l['notes']
        dt = parse_org_date(l['datetime'])
        assert isinstance(dt, datetime)
        ket = None if len(kets) == 0 else float(kets)
        glu = None if len(glus) == 0 else float(glus)
        yield Entry(
            dt=dt,
            ket=ket,
            glu=glu,
            extra=extra,
        )

def data():
    datas = list(iter_data())
    return list(sorted(datas, key=lambda d: d.dt))


def dataframe():
    import pandas as pd
    return pd.DataFrame(map(lambda e: e._asdict(), data()))


def main():
    print(data())


if __name__ == '__main__':
    main()
