import logging
from os import listdir
from os.path import join

from kython import json_load, JSONType
from kython.logging import setup_logzero

logger = logging.getLogger("rescuetime-provider")
setup_logzero(logger)


PATH = "/L/backups/rescuetime"

def try_load(fp: str):
    try:
        j: JSONType
        with open(fp, 'r') as fo:
            j = json_load(fo)

        if j is None:
            logger.warning(f"Corrupted: {fp}")
            return None

        return j
    except Exception as e:
        if 'Expecting value' in str(e):
            logger.warning(f"Corrupted: {fp}")
        else:
            raise e
    return None

from datetime import datetime, timedelta
from typing import NamedTuple, Dict, List

_DT_FMT = "%Y-%m-%dT%H:%M:%S"

class Entry(NamedTuple):
    dt: datetime # TODO mm, no timezone?
    duration_s: int

    @staticmethod
    def from_dict(row: Dict):
        dt_s = row['Date']
        dur = row['Time Spent (seconds)']
        dt = datetime.strptime(dt_s, _DT_FMT)
        return Entry(dt=dt, duration_s=dur)

    @staticmethod
    def from_row(row: List):
        COL_DT = 0
        COL_DUR = 1
        dt_s = row[COL_DT]
        dur = row[COL_DUR]
        dt = datetime.strptime(dt_s, _DT_FMT)
        return Entry(dt=dt, duration_s=dur)

from typing import Set
all_entries: Set[Entry] = set()

for f in sorted(listdir(PATH))[-5:]: # TODO FIXME
    fp = join(PATH, f)
    j = try_load(fp)
    if j is None:
        continue

    cols = j['row_headers']
    seen = 0
    total = 0
    for row in j['rows']:
        e = Entry.from_row(row)
        total += 1
        if e in all_entries:
            seen += 1
        else:
            all_entries.add(e)
    print(f"{f}: {seen}/{total}")
    # import ipdb; ipdb.set_trace()
    # print(len(j))

all_sorted = sorted(all_entries, key=lambda e: e.dt)
gap = timedelta(hours=3)

groups = []
group = []

for e in all_sorted:
    if len(group) > 0 and e.dt - group[-1].dt > gap:
        groups.append(group)
        group = []
    group.append(e)

if len(group) > 0:
    groups.append(group)
    group = []

for gr in groups:
    print(f"{gr[0].dt}--{gr[-1].dt}")


# TODO merged db?
# TODO ok, it summarises my sleep intervals pretty well. I guess should adjust it for the fact I don't sleep during the day, and it would be ok!

