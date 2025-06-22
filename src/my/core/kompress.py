from . import warnings

warnings.high('my.core.kompress is deprecated. Install and use "kompress" library directly in your module (see https://github.com/karlicoss/kompress )')

# in case some older user's modules aren't migrated, import all stuff from installed kompress into the scope
from kompress import *  # type: ignore[no-redef]  # complains about 'warnings' import
