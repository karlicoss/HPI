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
