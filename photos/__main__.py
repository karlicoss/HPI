import logging
logging.basicConfig(level=logging.INFO)

from kython.logging import setup_logzero

from photos import get_photos, iter_photos, get_logger

setup_logzero(get_logger(), level=logging.DEBUG)

import sys

if len(sys.argv) > 1:
    cmd = sys.argv[1]
    if cmd == "update_cache":
        from photos import update_cache, get_photos
        update_cache()
        get_photos(cached=True)
    else:
        raise RuntimeError(f"Unknown command {cmd}")
else:
    for p in iter_photos():
        pass
        # TODO need datetime!
        # print(p)
