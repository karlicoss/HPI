'''
Contains backwards compatibility helpers for different python versions, plus the warning category HPI passes to `deprecated`.
If something is relevant to HPI itself, please put it in .hpi_compat instead
'''

import sys

if sys.version_info[:2] >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated


class HPIDeprecationWarning(FutureWarning):
    """
    Warning category for deprecated HPI APIs, used as `@deprecated(..., category=HPIDeprecationWarning)`.

    Python hides the default `DeprecationWarning` unless the deprecated call comes from `__main__`,
      so users would not see it when the caller is an overlay module or a library such as Promnesia.
    `FutureWarning` is shown by default, and the subclass lets users filter HPI deprecations specifically.
    """
