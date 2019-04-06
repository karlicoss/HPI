import logging
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import NamedTuple, Dict, List, Set
from functools import lru_cache


from kython import JSONType, fget, group_by_cmp


def get_logger():
    return logging.getLogger("rescuetime-provider")

_PATH = Path("/L/backups/rescuetime")

def try_load(fp: Path):
    logger = get_logger()
    try:
        return json.loads(fp.read_text())
    except Exception as e:
        if 'Expecting value' in str(e):
            logger.warning(f"Corrupted: {fp}")
        else:
            raise e
    return None


_DT_FMT = "%Y-%m-%dT%H:%M:%S"

class Entry(NamedTuple):
    # TODO ugh, appears to be local time...
    dt: datetime
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


@lru_cache()
def get_rescuetime():
    entries: Set[Entry] = set()

    for fp in list(sorted(_PATH.glob('*.json')))[-5:]:
        j = try_load(fp)
        if j is None:
            continue

        cols = j['row_headers']
        seen = 0
        total = 0
        for row in j['rows']:
            e = Entry.from_row(row)
            total += 1
            if e in entries:
                seen += 1
            else:
                entries.add(e)
        print(f"{fp}: {seen}/{total}")
        # import ipdb; ipdb.set_trace()
        # print(len(j))
    res = sorted(entries, key=fget(Entry.dt))
    return res


def get_groups(gap=timedelta(hours=3)):
    data = get_rescuetime()
    return group_by_cmp(data, lambda a, b: (b.dt - a.dt) <= gap, dist=1)

