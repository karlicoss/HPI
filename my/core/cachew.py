# TODO this probably belongs to cachew? or cachew.experimental
from contextlib import contextmanager
from pathlib import Path


def disable_cachew():
    '''
    NOTE: you need to use it before importing any function using @cachew.cachew
    '''
    # TODO not sure... maybe it should instead use some hook.. it's a ibt ugly do
    import cachew

    @cachew.doublewrap
    def cachew_off(func=None, *args, **kwargs):
        return func
    old = cachew.cachew
    cachew.cachew = cachew_off
    return old


@contextmanager
def disabled_cachew():
    try:
        import cachew
    except ModuleNotFoundError:
        # no need to disable anything
        yield
        return
    old = disable_cachew()
    try:
        yield
    finally:
        cachew.cachew = old


def cache_dir() -> Path:
    '''
    Base directory for cachew.
    To override, add to your config file:
    class config:
        cache_dir = '/your/custom/cache/path'
    '''
    from .core_config import config
    cdir = config.cache_dir
    if cdir is None:
        # TODO handle this in core_config.py
        # TODO fallback to default cachew dir instead? or appdirs cache
        return Path('/var/tmp/cachew')
    else:
        return Path(cdir)
