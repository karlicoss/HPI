from . import warnings

warnings.high('my.core.kompress is deprecated. Install and use "kompress" library directly in your module (see https://github.com/karlicoss/kompress )')

from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    # in case some older user's modules aren't migrated, import all stuff from installed kompress into the scope
    from kompress import *
