"""
This is here temporarily, for backwards compatability purposes
It should be removed in the future, and you should replace any imports
like:
from my.reddit import ...
to:
from my.reddit.all import ...
since that allows for easier overriding using namespace packages
https://github.com/karlicoss/HPI/issues/102
"""

# TODO: add warning here

from .rexport import *
