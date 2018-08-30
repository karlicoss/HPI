from location import get_logger, get_locations, iter_locations

logger = get_logger()

from kython.logging import setup_logzero

setup_logzero(logger)

import sys

if len(sys.argv) > 1:
    cmd = sys.argv[1]
    if cmd == "update_cache":
        from location import update_cache, get_locations
        update_cache()
        get_locations(cached=True)
    else:
        raise RuntimeError(f"Unknown command {cmd}")
else:
    for p in iter_locations():
        pass
        # TODO need datetime!
        # print(p)
