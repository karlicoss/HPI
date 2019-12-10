import re
from typing import Tuple, Iterator
from datetime import date, datetime


from my_configuration.holidays_data import HOLIDAYS_DATA


def iter_data() -> Iterator[Tuple[date, int]]:
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
    assert emitted > 5


if __name__ == '__main__':
    for d in iter_data():
        print(d)
