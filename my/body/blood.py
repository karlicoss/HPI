"""
Blood tracking
"""

from datetime import datetime
from typing import Iterable, NamedTuple, Optional
from itertools import chain

import porg
from ..common import listify
from ..error import Res, echain


from kython.org import parse_org_date

from my.config import blood as config

import pandas as pd # type: ignore


class Entry(NamedTuple):
    dt: datetime

    ket: Optional[float]=None
    glu: Optional[float]=None

    vitd: Optional[float]=None
    b12: Optional[float]=None

    hdl: Optional[float]=None
    ldl: Optional[float]=None
    trig: Optional[float]=None

    extra: Optional[str]=None


Result = Res[Entry]

class ParseError(Exception):
    pass


def try_float(s: str) -> Optional[float]:
    l = s.split()
    if len(l) == 0:
        return None
    x = l[0].strip()
    if len(x) == 0:
        return None
    return float(x)


def iter_gluc_keto_data() -> Iterable[Result]:
    o = porg.Org.from_file(str(config.blood_log))
    tbl = o.xpath('//table')
    for l in tbl.lines:
        kets = l['ket'].strip()
        glus = l['glu'].strip()
        extra = l['notes']
        dt = parse_org_date(l['datetime'])
        assert isinstance(dt, datetime)
        ket = try_float(kets)
        glu = try_float(glus)
        yield Entry(
            dt=dt,
            ket=ket,
            glu=glu,
            extra=extra,
        )


def iter_tests_data() -> Iterable[Result]:
    o = porg.Org.from_file(str(config.blood_tests_log))
    tbl = o.xpath('//table')
    for d in tbl.lines:
        try:
            dt = parse_org_date(d['datetime'])
            assert isinstance(dt, datetime)
            # TODO rest

            F = lambda n: try_float(d[n])
            yield Entry(
                dt=dt,

                vitd=F('VD nm/L'),
                b12 =F('B12 pm/L'),

                hdl =F('HDL mm/L'),
                ldl =F('LDL mm/L'),
                trig=F('Trig mm/L'),

                extra=d['misc'],
            )
        except Exception as e:
            print(e)
            yield echain(ParseError(str(d)), e)


def data():
    datas = list(chain(iter_gluc_keto_data(), iter_tests_data()))
    return list(sorted(datas, key=lambda d: getattr(d, 'dt', datetime.min)))


@listify(wrapper=pd.DataFrame)
def dataframe():
    for d in data():
        if isinstance(d, Exception):
            yield {'error': str(d)}
        else:
            yield d._asdict()


def test():
    print(dataframe())
    assert len(dataframe()) > 10


def main():
    print(data())


if __name__ == '__main__':
    main()
