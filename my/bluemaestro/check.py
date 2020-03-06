#!/usr/bin/python3
import logging
from datetime import timedelta, datetime

from my.bluemaestro import measurements, logger

# TODO move this to backup checker?
def main():
    temps = list(measurements())
    latest = temps[:-2]

    prev, _ = latest[-2]
    last, _ = latest[-1]

    POINTS_STORED = 6000
    FREQ_SEC = 60
    SECS_STORED = POINTS_STORED * FREQ_SEC
    HOURS_STORED = POINTS_STORED / (60 * 60 / FREQ_SEC) # around 4 days
    NOW = datetime.now()
    assert NOW - last < timedelta(hours=HOURS_STORED / 2), f'old backup! {last}'


    assert last - prev  < timedelta(minutes=3), f'bad interval! {last - prev}'
    single = (last - prev).seconds



if __name__ == '__main__':
    main()
