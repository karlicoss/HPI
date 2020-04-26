# TODO this probably belongs to cachew? or cachew.experimental
from contextlib import contextmanager


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
    import cachew
    old = disable_cachew()
    try:
        yield
    finally:
        cachew.cachew = old
