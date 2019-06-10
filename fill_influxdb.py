#!/usr/bin/env python3
# pip install influxdb
from influxdb import InfluxDBClient # type: ignore
from my.lastfm import get_scrobbles


def main():
    scrobbles = get_scrobbles()
    client = InfluxDBClient()
    # TODO client.create_database('lastfm')

    jsons = [{"measurement": 'scrobble', "tags": {}, "time": str(sc.dt), "fields": {"name": sc.track}} for sc in scrobbles]
    client.write_points(jsons, database='lastfm')


if __name__ == '__main__':
    main()
