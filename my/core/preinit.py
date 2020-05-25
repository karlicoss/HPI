from pathlib import Path

def get_mycfg_dir() -> Path:
    import appdirs # type: ignore[import]
    import os
    # not sure if that's necessary, i.e. could rely on PYTHONPATH instead
    # on the other hand, by using MY_CONFIG we are guaranteed to load it from the desired path?
    mvar = os.environ.get('MY_CONFIG')
    if mvar is not None:
        mycfg_dir = Path(mvar)
    else:
        mycfg_dir = Path(appdirs.user_config_dir('my'))
    return mycfg_dir
