'''
A hook to insert user's config directory into Python's search path.

Ideally that would be in __init__.py (so it's executed without having to import explicityly)
But, with namespace packages, we can't have __init__.py in the parent subpackage
(see http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-init-py-trap)

Instead, this is imported in the stub config (in this repository), so if the stub config is used, it triggers import of the 'real' config.

Please let me know if you are aware of a better way of dealing with this!
'''


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

    # remove the stub and reimport the 'real' config
    # likely my.config will always be in sys.modules, but defensive just in case
    if 'my.config' in sys.modules:
        del sys.modules['my.config']
    # this should import from mpath now
    try:
        import my.config
    except ImportError as ex:
        # just in case... who knows what crazy setup users have
        import logging
        logging.exception(ex)
        warnings.warn(f"""
Importing 'my.config' failed! (error: {ex}). This is likely to result in issues.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-the-modules for more info.
""")


setup_config()
del setup_config
