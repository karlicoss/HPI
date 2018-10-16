from kython import json_load
from datetime import datetime
from os.path import join
from functools import lru_cache

from datetime import timedelta, datetime
from typing import List, Dict, Iterator

fromts = datetime.fromtimestamp

def hhmm(minutes):
    return '{:02d}:{:02d}'.format(*divmod(minutes, 60))

PATH = "/L/backups/emfit/"

AWAKE = 4

class Emfit:
    def __init__(self, jj):
        self.jj = jj

    @property
    def hrv_morning(self):
        return self.jj['hrv_rmssd_morning']

    @property
    def hrv_evening(self):
        return self.jj['hrv_rmssd_evening']

    @property
    def date(self):
        return self.end.date()

    @property
    def start(self):
        return fromts(self.jj['time_start'])

    @property
    def end(self):
        return fromts(self.jj['time_end'])

    @property
    def epochs(self):
        return self.jj['sleep_epoch_datapoints']

    @property # type: ignore
    @lru_cache()
    def sleep_start(self) -> datetime:
        for [ts, e] in self.epochs:
            if e == AWAKE:
                continue
            return fromts(ts)
        raise RuntimeError

    @property # type: ignore
    @lru_cache()
    def sleep_end(self) -> datetime:
        for [ts, e] in reversed(self.epochs):
            if e == AWAKE:
                continue
            return fromts(ts)
        raise RuntimeError
# 'sleep_epoch_datapoints'
# [[timestamp, number]]

    # so it's actual sleep, without awake
    # ok, so I need time_asleep
    @property
    def sleep_minutes(self):
        return self.jj['sleep_duration'] // 60

    @property
    def hrv_lf(self):
        return self.jj['hrv_lf']

    @property
    def hrv_hf(self):
        return self.jj['hrv_hf']

    @property
    def summary(self):
        return f"""
slept for {hhmm(self.sleep_minutes)}
hrv morning: {self.hrv_morning:.0f}
hrv evening: {self.hrv_evening:.0f}
recovery: {self.hrv_morning - self.hrv_evening:3.0f}
{self.hrv_lf}/{self.hrv_hf}""".replace('\n', ' ')


    def __str__(self) -> str:
        return f"from {self.sleep_start} to {self.sleep_end}"

# measured_datapoints
# [[timestamp, pulse, breath?, ??? hrv?]] # every 4 seconds?
    @property
    def sleep_hr(self):
        tss = []
        res = []
        for ll in self.jj['measured_datapoints']:
            [ts, pulse, br, activity] = ll
            # TODO what the fuck is whaat?? It can't be HRV, it's about 500 ms on average
            # act in csv.. so it must be activity? wonder how is it measured.
            # but I guess makes sense. yeah,  "measured_activity_avg": 595, about that
            # makes even more sense given tossturn datapoints only have timestamp
            if self.sleep_start < fromts(ts) < self.sleep_end:
                tss.append(ts)
                res.append(pulse)
        return tss, res

    @property
    def hrv(self):
        tss = []
        res = []
        for ll in self.jj['hrv_rmssd_datapoints']:
            [ts, rmssd, _, _, almost_always_zero, _] = ll
            # timestamp,rmssd,tp,lfn,hfn,r_hrv
            # TP is total_power??
            # erm. looks like there is a discrepancy between csv and json data.
            # right, so web is using api v 1. what if i use v1??
            # definitely a discrepancy between v1 and v4. have no idea how to resolve it :(
            # also if one of them is indeed tp value, it must have been rounded.
            # TODO what is the meaning of the rest???
            # they don't look like HR data.
            tss.append(ts)
            res.append(rmssd)
        return tss, res

    @property
    def measured_hr_avg(self):
        return self.jj["measured_hr_avg"]

    @property
    def sleep_hr_coverage(self):
        tss, hrs = self.sleep_hr
        covered_sec = len([h for h in hrs if h is not None])
        expected_sec = self.sleep_minutes * 60 / 4
        return covered_sec / expected_sec * 100

def iter_datas() -> Iterator[Emfit]:
    import os
    for f in sorted(os.listdir(PATH)):
        if not f.endswith('.json'):
            continue

        with open(join(PATH, f), 'r') as fo:
            ef = Emfit(json_load(fo))
            yield ef

def get_datas() -> List[Emfit]:
    return list(sorted(list(iter_datas()), key=lambda e: e.start))
