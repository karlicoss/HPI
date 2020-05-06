"""
Public holidays (automatic) and days off work (manual inputs)
"""

from functools import lru_cache
from datetime import date, datetime, timedelta
import re
from typing import Tuple, Iterator, List, Union


from my.config.holidays_data import HOLIDAYS_DATA


# pip3 install workalendar
from workalendar.europe import UnitedKingdom # type: ignore
cal = UnitedKingdom() # TODO
# TODO that should depend on country/'location' of residence I suppose?


Dateish = Union[datetime, date, str]


def as_date(dd: Dateish) -> date:
    if isinstance(dd, datetime):
        return dd.date()
    elif isinstance(dd, date):
        return dd
    else:
        return as_date(datetime.strptime(dd, '%Y%m%d'))


@lru_cache(1)
def get_days_off_work() -> List[date]:
    return list(iter_days_off_work())


def is_day_off_work(d: date) -> bool:
    return d in get_days_off_work()


def is_working_day(d: Dateish) -> bool:
    day = as_date(d)
    if not cal.is_working_day(day):
        # public holiday -- def holiday
        return False
    # otherwise rely on work data
    return not is_day_off_work(day)


def is_holiday(d: Dateish) -> bool:
    return not(is_working_day(d))


def _iter_work_data() -> Iterator[Tuple[date, int]]:
    emitted = 0
    for x in HOLIDAYS_DATA.splitlines():
        m = re.search(r'(\d\d/\d\d/\d\d\d\d)(.*)-(\d+.\d+) days \d+.\d+ days', x)
        if m is None:
            continue
        (ds, cmnt, dayss) = m.groups()
        if 'carry over' in cmnt:
            continue

        d = datetime.strptime(ds, '%d/%m/%Y').date()
        dd, u = dayss.split('.')
        assert u == '00' # TODO meh

        yield d, int(dd)
        emitted += 1
    assert emitted > 5 # arbitrary, just a sanity check.. (TODO move to tests?)


def iter_days_off_work() -> Iterator[date]:
    for d, span in _iter_work_data():
        dd = d
        while span > 0:
            # only count it if it wasnt' a public holiday/weekend already
            if cal.is_working_day(dd):
                yield dd
                span -= 1
            dd += timedelta(days=1)


def test():
    assert is_holiday('20190101')
    assert not is_holiday('20180601')


if __name__ == '__main__':
    for d in iter_days_off_work():
        print(d, ' | ', d.strftime('%d %b'))
