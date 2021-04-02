'''
A hook to insert user's config directory into Python's search path.

- Ideally that would be in __init__.py (so it's executed without having to import explicityly)
  But, with namespace packages, we can't have __init__.py in the parent subpackage
  (see http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-init-py-trap)

  Please let me know if you are aware of a better way of dealing with this!
'''

from types import ModuleType

# TODO not ideal to keep it here, but this should really be a leaf in the import tree
# TODO maybe I don't even need it anymore?
def assign_module(parent: str, name: str, module: ModuleType) -> None:
    import sys
    import importlib
    parent_module = importlib.import_module(parent)
    sys.modules[parent + '.' + name] = module
    if sys.version_info.minor == 6:
        # ugh. not sure why it's necessary in py36...
        # TODO that crap should be tested... I guess will get it for free when I run rest of tests in the matrix
        setattr(parent_module, name, module)

del ModuleType


# separate function to present namespace pollution
def setup_config() -> None:
    import sys
    import warnings

    from .preinit import get_mycfg_dir
    mycfg_dir = get_mycfg_dir()

    if not mycfg_dir.exists():
        warnings.warn(f"""
'my.config' package isn't found! (expected at '{mycfg_dir}'). This is likely to result in issues.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-the-modules for more info.
""".strip())
        return

    mpath = str(mycfg_dir)
    # NOTE: we _really_ want to have mpath in front there, to shadow my.config stub within this packages
    # hopefully it doesn't cause any issues
    sys.path.insert(0, mpath)

    # remove the stub and insert reimport hte 'real' config
    if 'my.config' in sys.modules:
        # TODO FIXME make sure this method isn't called twice...
        del sys.modules['my.config']
    try:
        # todo import_from instead?? dunno
        import my.config
    except ImportError as ex:
        # just in case... who knows what crazy setup users have in mind.
        # todo log?
        warnings.warn(f"""
Importing 'my.config' failed! (error: {ex}). This is likely to result in issues.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-the-modules for more info.
""")


setup_config()
del setup_config
