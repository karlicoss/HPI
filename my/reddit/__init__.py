"""
This is here temporarily, for backwards compatibility purposes
It should be removed in the future, and you should replace any imports
like:
from my.reddit import ...
to:
from my.reddit.all import ...
since that allows for easier overriding using namespace packages
https://github.com/karlicoss/HPI/issues/102
"""

# For now, including this here, since importing the module
# causes .rexport to be imported, which requires rexport
REQUIRES = [
    'git+https://github.com/karlicoss/rexport',
]

import re
import traceback

# some hacky traceback to inspect the current stack
# to see if the user is using the old style of importing
warn = False
for f in traceback.extract_stack():
    line = f.line or '' # just in case it's None, who knows..

    # cover the most common ways of previously interacting with the module
    if 'import my.reddit ' in (line + ' '):
        warn = True
    elif 'from my import reddit' in line:
        warn = True
    elif re.match(r"from my\.reddit\simport\s(comments|saved|submissions|upvoted)", line):
        warn = True

# TODO: add link to instructions to migrate
if warn:
    from my.core import warnings as W
    W.high("DEPRECATED! Instead of my.reddit, import from my.reddit.all instead.")


from .rexport import *
