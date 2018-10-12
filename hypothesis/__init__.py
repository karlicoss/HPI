from functools import lru_cache
from kython import listdir_abs, json_load, JSONType
from typing import Dict, List, NamedTuple
from pytz import UTC
from datetime import datetime
import os

_PATH = '/L/backups/hypothesis/'

class Entry(NamedTuple):
    dt: datetime
    summary: str
    content: str
    link: str
    eid: str

# TODO guarantee order?
def _iter():
    last = max(listdir_abs(_PATH))
    j: JSONType
    with open(last, 'r') as fo:
        j = json_load(fo)
    for i in j:
        dts = i['created']
        title = ' '.join(i['document']['title'])
        selectors = i['target'][0].get('selector', None)
        if selectors is None:
            # TODO warn?...
            selectors = []
        content = None
        for s in selectors:
            if 'exact' in s:
                content = s['exact']
                break
        eid = i['id']
        link = i['uri']
        dt = datetime.strptime(dts[:-3] + dts[-2:], '%Y-%m-%dT%H:%M:%S.%f%z')
        yield Entry(
            dt,
            title,
            content,
            link,
            eid,
        )


def get_entries():
    return list(_iter())
