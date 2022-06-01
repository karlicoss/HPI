"""
This is here temporarily, for backwards compatibility purposes
It should be removed in the future, and you should replace any imports
like:
from my.fbmessenger import ...
to:
from my.fbmessenger.export import ...
since that allows for easier overriding using namespace packages
https://github.com/karlicoss/HPI/issues/102
"""
# TODO ^^ later, replace the above with from my.fbmessenger.all, when we add more data sources

import re
import inspect


mname = __name__.split('.')[-1]

# allow stuff like 'import my.module.submodule' and such
imported_as_parent = False

# allow stuff like 'from my.module import submodule'
importing_submodule = False

# some hacky traceback to inspect the current stack
# to see if the user is using the old style of importing
for f in inspect.stack():
    # seems that when a submodule is imported, at some point it'll call some internal import machinery
    # with 'parent' set to the parent module
    # if parent module is imported first (i.e. in case of deprecated usage), it won't be the case
    args = inspect.getargvalues(f.frame)
    if args.locals.get('parent') == f'my.{mname}':
        imported_as_parent = True

    # this we can only detect from the code I guess
    line = '\n'.join(f.code_context or [])
    if re.match(rf'from\s+my\.{mname}\s+import\s+export', line):
        # todo 'export' is hardcoded, not sure how to infer allowed objects anutomatically..
        importing_submodule = True

legacy = not (imported_as_parent or importing_submodule)

if legacy:
    from my.core import warnings as W
    # TODO: add link to instructions to migrate
    W.high("DEPRECATED! Instead of my.fbmessengerexport, import from my.fbmessengerexport.export")
    # only import in legacy mode
    # otherswise might have unfortunate side effects (e.g. missing imports)
    from .export import *

# kinda annoying to keep it, but it's so legacy 'hpi module install my.fbmessenger' work
# needs to be on the top level (since it's extracted via ast module), but hopefully it doesn't hurt here
REQUIRES = [
    'git+https://github.com/karlicoss/fbmessengerexport',
]


# to prevent it from apprearing in modules list/doctor
from ..core import __NOT_HPI_MODULE__

###
# this is to trick mypy into treating this as a proper namespace package
# should only be used for backwards compatibility on packages that are convernted into namespace & all.py pattern
# - https://www.python.org/dev/peps/pep-0382/#namespace-packages-today
# - https://github.com/karlicoss/hpi_namespace_experiment
# - discussion here https://memex.zulipchat.com/#narrow/stream/279601-hpi/topic/extending.20HPI/near/269946944
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
# 'this' source tree ends up first in the pythonpath when we extend_path()
# so we need to move 'this' source tree towards the end to make sure we prioritize overlays
__path__ = __path__[1:] + __path__[:1]
###
