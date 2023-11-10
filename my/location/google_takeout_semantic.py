"""
Extracts semantic location history using google_takeout_parser
"""

# This is a separate module to prevent ImportError and a new config block from breaking
# previously functional my.location.google_takeout locations

REQUIRES = ["git+https://github.com/seanbreckenridge/google_takeout_parser"]

from typing import Iterator, List

from my.google.takeout.parser import events, _cachew_depends_on as _parser_cachew_depends_on
from google_takeout_parser.models import PlaceVisit as SemanticLocation

from my.core import dataclass, make_config
from my.core.common import mcachew, LazyLogger, Stats
from my.core.error import Res
from .common import Location

logger = LazyLogger(__name__)

from my.config import location as user_config

@dataclass
class semantic_locations_config(user_config.google_takeout_semantic):
    # a value between 0 and 100, 100 being the most confident
    # set to 0 to include all locations
    # https://locationhistoryformat.com/reference/semantic/#/$defs/placeVisit/properties/locationConfidence
    require_confidence: int = 40
    # default accuracy for semantic locations
    accuracy: float = 100.0


config = make_config(semantic_locations_config)


# add config to cachew dependency so it recomputes on config changes
def _cachew_depends_on() -> List[str]:
    dep = _parser_cachew_depends_on()
    dep.insert(0, f"require_confidence={config.require_confidence} accuracy={config.accuracy}")
    return dep



@mcachew(
    depends_on=_cachew_depends_on,
    logger=logger,
)
def locations() -> Iterator[Res[Location]]:
    require_confidence = config.require_confidence
    if require_confidence < 0 or require_confidence > 100:
        yield ValueError("location.google_takeout.semantic_require_confidence must be between 0 and 100")
        return

    for g in events():
        if isinstance(g, SemanticLocation):
            visitConfidence = g.visitConfidence
            if visitConfidence is None or visitConfidence < require_confidence:
                logger.debug(f"Skipping {g} due to low confidence ({visitConfidence}))")
                continue
            yield Location(
                lon=g.lng,
                lat=g.lat,
                dt=g.dt,
                # can accuracy be inferred from visitConfidence?
                # there's no exact distance value in the data, its a 0-100% confidence value...
                accuracy=config.accuracy,
                elevation=None,
                datasource="google_takeout_semantic",
            )



def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
