'''
NOTE: you shouldn't modify this file.
You probably want to edit your personal config (check via 'hpi config check' or create with 'hpi config create').

See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-modules for info on creating your own config

This file is used for:
- documentation (as an example of the config structure)
- mypy: this file provides some type annotations
- for loading the actual user config
'''
#### NOTE: you won't need this line VVVV in your personal config
from my.core import init
###


from datetime import tzinfo
from pathlib import Path
from typing import List


from my.core import Paths, PathIsh


class hypothesis:
    # expects outputs from https://github.com/karlicoss/hypexport
    # (it's just the standard Hypothes.is export format)
    export_path: Paths = r'/path/to/hypothesis/data'

class instapaper:
    export_path: Paths = ''

class smscalls:
    export_path: Paths = ''

class pocket:
    export_path: Paths = ''

class github:
    export_path: Paths = ''

    gdpr_dir: Paths = ''

class reddit:
    class rexport:
        export_path: Paths = ''
    class pushshift:
        export_path: Paths = ''
    class gdpr:
        export_path: Paths = ''

class endomondo:
    export_path: Paths = ''

class exercise:
    workout_log: PathIsh = '/some/path.org'

class bluemaestro:
    export_path: Paths = ''

class stackexchange:
    export_path: Paths = ''

class goodreads:
    export_path: Paths = ''

class pinboard:
    export_dir: Paths = ''

class google:
    takeout_path: Paths = ''


from typing import Sequence, Union, Tuple
from datetime import datetime, date, timedelta
DateIsh = Union[datetime, date, str]
LatLon = Tuple[float, float]
class location:
    # todo ugh, need to think about it... mypy wants the type here to be general, otherwise it can't deduce
    # and we can't import the types from the module itself, otherwise would be circular. common module?
    home: Union[LatLon, Sequence[Tuple[DateIsh, LatLon]]] = (1.0, -1.0)
    home_accuracy = 30_000.0

    class via_ip:
        accuracy: float
        for_duration: timedelta

    class gpslogger:
        export_path: Paths = ''
        accuracy: float

    class google_takeout_semantic:
        # a value between 0 and 100, 100 being the most confident
        # set to 0 to include all locations
        # https://locationhistoryformat.com/reference/semantic/#/$defs/placeVisit/properties/locationConfidence
        require_confidence: float = 40
        # default accuracy for semantic locations
        accuracy: float = 100


from typing import Literal
class time:
    class tz:
        policy: Literal['keep', 'convert', 'throw']

        class via_location:
            fast: bool
            sort_locations: bool
            require_accuracy: float


class orgmode:
    paths: Paths


class arbtt:
    logfiles: Paths


from typing import Optional
class commits:
    emails: Optional[Sequence[str]]
    names: Optional[Sequence[str]]
    roots: Sequence[PathIsh]


class pdfs:
    paths: Paths


class zulip:
    class organization:
        export_path: Paths


class bumble:
    class android:
        export_path: Paths


class tinder:
    class android:
        export_path: Paths


class instagram:
    class android:
        export_path: Paths
        username: Optional[str]
        full_name: Optional[str]

    class gdpr:
        export_path: Paths


class hackernews:
    class dogsheep:
        export_path: Paths


class materialistic:
    export_path: Paths


class fbmessenger:
    class fbmessengerexport:
        export_db: PathIsh
        facebook_id: Optional[str]
    class android:
        export_path: Paths


class twitter_archive:
    export_path: Paths


class twitter:
    class talon:
        export_path: Paths


class twint:
    export_path: Paths


class browser:
    class export:
        export_path: Paths = ''
    class active_browser:
        export_path: Paths = ''


class telegram:
    class telegram_backup:
        export_path: PathIsh = ''


class demo:
    data_path: Paths
    username: str
    timezone: tzinfo


class simple:
    count: int


class vk_messages_backup:
    storage_path: Path
    user_id: int


class kobo:
    export_path: Paths


class feedly:
    export_path: Paths


class feedbin:
    export_path: Paths


class taplog:
    export_path: Paths


class lastfm:
    export_path: Paths


class rescuetime:
    export_path: Paths


class runnerup:
    export_path: Paths


class emfit:
    export_path: Path
    timezone: tzinfo
    excluded_sids: List[str]


class foursquare:
    export_path: Paths


class rtm:
    export_path: Paths


class imdb:
    export_path: Paths


class roamresearch:
    export_path: Paths
    username: str


class whatsapp:
    class android:
        export_path: Paths
        my_user_id: Optional[str]


class harmonic:
    export_path: Paths
