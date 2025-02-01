from pathlib import Path


# todo preinit isn't really a good name? it's only in a separate file because
# - it's imported from my.core.init (so we wan't to keep this file as small/reliable as possible, hence not common or something)
# - we still need this function in __main__, so has to be separate from my/core/init.py
def get_mycfg_dir() -> Path:
    import os

    import platformdirs

    # not sure if that's necessary, i.e. could rely on PYTHONPATH instead
    # on the other hand, by using MY_CONFIG we are guaranteed to load it from the desired path?
    mvar = os.environ.get('MY_CONFIG')
    if mvar is not None:
        mycfg_dir = Path(mvar)
    else:
        mycfg_dir = Path(platformdirs.user_config_dir('my'))
    return mycfg_dir
