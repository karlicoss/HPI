#!/usr/bin/env python3.6
from kython import *

from backup_config import SLEEPS_FILE, GRAPHS_DIR

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

    def graph(self) -> str:
        return os.path.join(GRAPHS_DIR, self.xid() + ".png")

    def __str__(self) -> str:
        return f"{self.date_()} {self.title()}"

    def __repr__(self) -> str:
        return str(self)

def load_sleeps() -> List[SleepEntry]:
    with open(SLEEPS_FILE, 'r') as fo:
        sleeps = json_load(fo)
        return [SleepEntry(js) for js in sleeps]

sleeps = load_sleeps()
# TODO use map?
sleep = sleeps[0]
# pprint(sleeps[:2])


span = sleep.completed() - sleep.created()
print(f"span: {span}")
import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
# pip install imageio
from imageio import imread # type: ignore

img = imread(sleep.graph())
# all of them are 300x300 images apparently
(a, b, _) = img.shape
# print(img.shape)
# print(img.size)
print(a)
print(b)

np.random.seed(0)
x = np.random.uniform(0.0, a, 100)
y = np.random.uniform(0.0, b, 100)
plt.scatter(x,y,zorder=1)
plt.imshow(img,zorder=0)
plt.title(str(sleep))
plt.text(0, 0, str(sleep.created().time()))
plt.text(300, 0, str(sleep.completed().time()))
plt.show()

