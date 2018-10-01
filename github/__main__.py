from github import get_events, get_logger
from kython import setup_logzero

logger = get_logger()
setup_logzero(logger)

for e in get_events():
    print(e)
