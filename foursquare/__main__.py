from foursquare import get_checkins, get_logger, cleanup_backups

import logging
from kython.logging import setup_logzero

logger = get_logger()
setup_logzero(logger, level=logging.INFO)

cleanup_backups()

# for c in get_checkins():
#     print(c)

