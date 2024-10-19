'''
A hook to insert user's config directory into Python's search path.
Note that this file is imported only if we don't have custom user config (under my.config namespace) in PYTHONPATH

Ideally that would be in __init__.py (so it's executed without having to import explicitly)
But, with namespace packages, we can't have __init__.py in the parent subpackage
(see http://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html#the-init-py-trap)

Instead, this is imported in the stub config (in this repository), so if the stub config is used, it triggers import of the 'real' config.

Please let me know if you are aware of a better way of dealing with this!
'''


# separate function to present namespace pollution
def setup_config() -> None:
    import sys
    import warnings
    from pathlib import Path

    from .preinit import get_mycfg_dir

    mycfg_dir = get_mycfg_dir()

    if not mycfg_dir.exists():
        warnings.warn(f"""
'my.config' package isn't found! (expected at '{mycfg_dir}'). This is likely to result in issues.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-the-modules for more info.
""".strip(), stacklevel=1)
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
""", stacklevel=1)
    else:
        # defensive just in case -- __file__ may not be present if there is some dynamic magic involved
        used_config_file = getattr(my.config, '__file__', None)
        if used_config_file is not None:
            used_config_path = Path(used_config_file)
            try:
                # will crash if it's imported from other dir?
                used_config_path.relative_to(mycfg_dir)
            except ValueError:
                # TODO maybe implement a strict mode where these warnings will be errors?
                warnings.warn(
                    f"""
Expected my.config to be located at {mycfg_dir}, but instead its path is {used_config_path}.
This will likely cause issues down the line -- double check {mycfg_dir} structure.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-the-modules for more info.
""", stacklevel=1
                    )


setup_config()
del setup_config
