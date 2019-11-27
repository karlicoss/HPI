from kython.klogging import setup_logzero

from . import get_logger, get_groups, get_rescuetime, fill_influxdb

def main():
    logger = get_logger()
    setup_logzero(logger)

    # for gr in get_groups():
    #     print(f"{gr[0].dt}--{gr[-1].dt}")
    # for e in get_rescuetime(latest=2):
    #     print(e)
    fill_influxdb()

    # TODO merged db?
    # TODO ok, it summarises my sleep intervals pretty well. I guess should adjust it for the fact I don't sleep during the day, and it would be ok!

if __name__ == '__main__':
    main()
