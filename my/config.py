'''
NOTE: you shouldn't modify this file.
You probably want to edit your personal config (check via 'hpi config check' or create with 'hpi config create').

See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-modules for info on creating your own config

This file is used for:
- documentation (as an example of the config structure)
- mypy: this file provides some type annotations
- for loading the actual user config
'''
#### vvvv you won't need this VVV in your personal config
from my.core import init
###


from my.core import Paths, PathIsh

class hypothesis:
    # expects outputs from https://github.com/karlicoss/hypexport
    # (it's just the standard Hypothes.is export format)
    export_path: Paths = '/path/to/hypothesis/data'

class instapaper:
    export_path: Paths = ''

class pocket:
    export_path: Paths = ''

class github:
    export_path: Paths = ''

class reddit:
    export_path: Paths = ''

class endomondo:
    export_path: Paths = ''

class exercise:
    workout_log: PathIsh = '/some/path.org'

class bluemaestro:
    export_path: Paths = ''

class stackexchange:
    export_path: Paths = ''

class pinboard:
    export_dir: Paths = ''

class google:
    takeout_path: Paths = ''


from typing import Sequence, Union, Tuple
from datetime import datetime, date
DateIsh = Union[datetime, date, str]
LatLon = Tuple[float, float]
class location:
    # todo ugh, need to think about it... mypy wants the type here to be general, otherwise it can't deduce
    # and we can't import the types from the module itself, otherwise would be circular. common module?
    home: Union[LatLon, Sequence[Tuple[DateIsh, LatLon]]] = (1.0, -1.0)


class time:
    class tz:
        pass


class orgmode:
    paths: Paths
