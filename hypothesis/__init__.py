from functools import lru_cache
from kython import listdir_abs, json_load, JSONType
from typing import Dict, List, NamedTuple
from pytz import UTC
from datetime import datetime
import os

# TODO maybe, it should generate some kind of html snippet?


_PATH = '/L/backups/hypothesis/'

class Hypothesis(NamedTuple):
    dt: datetime
    text: str
    tag: str

# TODO guarantee order?
def _iter():
    last = max(listdir_abs(_PATH))
    j: JSONType
    with open(last, 'r') as fo:
        j = json_load(fo)
    for i in j:
        dts = i['created']
        title = ' '.join(i['document']['title'])
        dt = datetime.strptime(dts[:-3] + dts[-2:], '%Y-%m-%dT%H:%M:%S.%f%z')
        yield Hypothesis(dt, title, 'hyp')


@lru_cache()
def get_entries():
    return list(_iter())
