import sys
import logging

from location import get_logger, get_locations, iter_locations, get_groups

from kython.klogging import setup_logzero

logger = get_logger()
setup_logzero(logger, level=logging.INFO)



if len(sys.argv) > 1:
    cmd = sys.argv[1]
    if cmd == "update_cache":
        from location import update_cache, get_locations
        update_cache()
        get_locations(cached=True)
    else:
        raise RuntimeError(f"Unknown command {cmd}")
else:
    for p in get_groups(cached=True):
        print(p)
        # TODO need datetime!
