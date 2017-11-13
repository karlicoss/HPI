#!/usr/bin/env python3.6
from kython import *

from backup_config import SLEEPS_FILE

from datetime import datetime
from datetime import date

XID = str # TODO how to shared with backup thing?

class SleepEntry:
    def __init__(self, js) -> None:
        self.js = js

    # TODO @memoize decorator?
    def date_(self) -> date:
        dates = str(self.js['date'])
        return datetime.strptime(dates, "%Y%m%d").date()

    def title(self) -> str:
        return self.js['title']

    def xid(self) -> XID:
        return self.js['xid']

    def _details(self):
        return self.js['details']

    # TODO take timezones into account?
    def created(self) -> datetime:
        return datetime.fromtimestamp(self.js['time_created'])

    def completed(self) -> datetime:
        return datetime.fromtimestamp(self.js['time_completed'])

    def __str__(self) -> str:
        return f"{self.date_()} {self.title()}"

    def __repr__(self) -> str:
        return str(self)

def load_sleeps() -> List[SleepEntry]:
    with open(SLEEPS_FILE, 'r') as fo:
        sleeps = json_load(fo)
        return [SleepEntry(js) for js in sleeps]

sleeps = load_sleeps()
pprint(sleeps[:2])
