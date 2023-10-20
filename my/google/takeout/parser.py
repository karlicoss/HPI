"""
Parses Google Takeout using [[https://github.com/seanbreckenridge/google_takeout_parser][google_takeout_parser]]

See [[https://github.com/seanbreckenridge/google_takeout_parser][google_takeout_parser]] for more information
about how to export and organize your takeouts

If the DISABLE_TAKEOUT_CACHE environment variable is set, this won't cache individual
exports in ~/.cache/google_takeout_parser

The directory set as takeout_path can be unpacked directories, or
zip files of the exports, which are temporarily unpacked while creating
the cachew cache
"""

REQUIRES = ["git+https://github.com/seanbreckenridge/google_takeout_parser"]

from contextlib import ExitStack
import os
from typing import List, Sequence, cast
from pathlib import Path
from my.core import make_config, dataclass
from my.core.common import Stats, LazyLogger, mcachew, get_files, Paths
from my.core.error import ErrorPolicy
from my.core.structure import match_structure

from my.core.time import user_forced
from google_takeout_parser.parse_html.html_time_utils import ABBR_TIMEZONES
ABBR_TIMEZONES.extend(user_forced())

import google_takeout_parser
from google_takeout_parser.path_dispatch import TakeoutParser
from google_takeout_parser.merge import GoogleEventSet, CacheResults

# see https://github.com/seanbreckenridge/dotfiles/blob/master/.config/my/my/config/__init__.py for an example
from my.config import google as user_config


@dataclass
class google(user_config):
    # directory which includes unpacked/zipped takeouts
    takeout_path: Paths

    error_policy: ErrorPolicy = 'yield'

    # experimental flag to use core.kompress.ZipPath
    # instead of unpacking to a tmp dir via match_structure
    _use_zippath: bool = False


config = make_config(google)


logger = LazyLogger(__name__, level="warning")

# patch the takeout parser logger to match the computed loglevel
from google_takeout_parser.log import setup as setup_takeout_logger
setup_takeout_logger(logger.level)


DISABLE_TAKEOUT_CACHE = "DISABLE_TAKEOUT_CACHE" in os.environ


def inputs() -> Sequence[Path]:
    return get_files(config.takeout_path)


EXPECTED = (
    "My Activity",
    "Chrome",
    "Location History",
    "Youtube",
    "YouTube and YouTube Music",
)


google_takeout_version = str(getattr(google_takeout_parser, '__version__', 'unknown'))

def _cachew_depends_on() -> List[str]:
    exports = sorted([str(p) for p in inputs()])
    # add google takeout parser pip version to hash, so this re-creates on breaking changes
    exports.insert(0, f"google_takeout_version: {google_takeout_version}")
    return exports


# ResultsType is a Union of all of the models in google_takeout_parser
@mcachew(depends_on=_cachew_depends_on, logger=logger, force_file=True)
def events(disable_takeout_cache: bool = DISABLE_TAKEOUT_CACHE) -> CacheResults:
    error_policy = config.error_policy
    count = 0
    emitted = GoogleEventSet()
    # reversed shouldn't really matter? but logic is to use newer
    # takeouts if they're named according to date, since JSON Activity
    # is nicer than HTML Activity
    for path in reversed(inputs()):
        with ExitStack() as exit_stack:
            if config._use_zippath:
                # for later takeouts it's just 'Takeout' dir,
                # but for older (pre 2015) it contains email/date in the subdir name
                results = tuple(cast(Sequence[Path], path.iterdir()))
            else:
                results = exit_stack.enter_context(match_structure(path, expected=EXPECTED, partial=True))
            for m in results:
                # e.g. /home/sean/data/google_takeout/Takeout-1634932457.zip") -> 'Takeout-1634932457'
                # means that zipped takeouts have nice filenames from cachew
                cw_id, _, _ = path.name.rpartition(".")
                # each takeout result is cached as well, in individual databases per-type
                tk = TakeoutParser(m, cachew_identifier=cw_id, error_policy=error_policy)
                # TODO might be nice to pass hpi cache dir?
                for event in tk.parse(cache=not disable_takeout_cache):
                    count += 1
                    if isinstance(event, Exception):
                        if error_policy == 'yield':
                            yield event
                        elif error_policy == 'raise':
                            raise event
                        elif error_policy == 'drop':
                            pass
                        continue
                    if event in emitted:
                        continue
                    emitted.add(event)
                    yield event  # type: ignore[misc]
    logger.debug(
        f"HPI Takeout merge: from a total of {count} events, removed {count - len(emitted)} duplicates"
    )


def stats() -> Stats:
    from my.core import stat

    return {
        **stat(events),
    }
