#!/usr/bin/python3
import logging
from datetime import timedelta, datetime
from kython import setup_logzero

from my.bluemaestro import get_temperature, get_logger

def main():
    setup_logzero(get_logger(), level=logging.DEBUG)

    temps = get_temperature()
    latest = sorted(temps.items())[:-2]

    prev, _ = latest[-2]
    last, _ = latest[-1]
    assert last - prev  < timedelta(minutes=3), f'bad interval! {last - prev}'
    single = (last - prev).seconds

    NOW = datetime.now()
    assert NOW - last < timedelta(days=5), f'old backup! {last}'


if __name__ == '__main__':
    main()
