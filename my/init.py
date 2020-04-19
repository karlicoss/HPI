'''
A hook to insert user's config directory into Python's search path.

- Ideally that would be in __init__.py (so it's executed without having to import explicityly)
  But, with namespace packages, we can't have __init__.py in the parent subpackage
  (see http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-init-py-trap)

  Please let me know if you are aware of a better way of dealing with this!
'''


# TODO not ideal to keep it here, but this should really be a leaf in the import tree
def assign_module(parent: str, name: str, module):
    import sys
    import importlib
    parent_module = importlib.import_module(parent)
    sys.modules[parent + '.' + name] = module
    if sys.version_info.minor == 6:
        # ugh. not sure why it's necessary in py36...
        # TODO that crap should be tested... I guess will get it for free when I run rest of tests in the matrix
        setattr(parent_module, name, module)


# separate function to present namespace pollution
def setup_config():
    from pathlib import Path
    import sys
    import os
    import warnings

    # not sure if that's necessary, i.e. could rely on PYTHONPATH instead
    # on the other hand, by using MY_CONFIG we are guaranteed to load it from the desired path?
    mvar = os.environ.get('MY_CONFIG')
    if mvar is not None:
        mycfg_dir = Path(mvar)
    else:
        # TODO use appdir??
        cfg_dir = Path('~/.config').expanduser()
        mycfg_dir = cfg_dir / 'my'

    # TODO maybe try importing first and if it's present, don't do anything?

    if not mycfg_dir.exists():
        warnings.warn(f"my.config package isn't found! (expected at {mycfg_dir}). This might result in issues.")
        from . import mycfg_stub as mycfg
        assign_module('my', 'config', mycfg)
    else:
        mp = str(mycfg_dir)
        if mp not in sys.path:
            sys.path.insert(0, mp)

    try:
        import my.config
    except ImportError as ex:
        warnings.warn(f"Importing my.config failed! (error: {ex}). This might result in issues.")


setup_config()
del setup_config
