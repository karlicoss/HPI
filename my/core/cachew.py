from contextlib import contextmanager
from pathlib import Path
from typing import Optional

# can lead to some unexpected issues if you 'import cachew' which being in my/core directory.. so let's protect against it
# NOTE: if we use overlay, name can be smth like my.origg.my.core.cachew ...
assert 'my.core' in __name__, f'Expected module __name__ ({__name__}) to start with my.core'

def disable_cachew() -> None:
    try:
        import cachew
    except ImportError:
        # nothing to disable
        return

    from cachew import settings
    settings.ENABLE = False


from typing import Iterator
@contextmanager
def disabled_cachew() -> Iterator[None]:
    try:
        import cachew
    except ImportError:
        # nothing to disable
        yield
        return
    from cachew.extra import disabled_cachew
    with disabled_cachew():
        yield


def _appdirs_cache_dir() -> Path:
    import appdirs # type: ignore
    cd = Path(appdirs.user_cache_dir('my'))
    cd.mkdir(exist_ok=True, parents=True)
    return cd


def cache_dir() -> Optional[Path]:
    from . import core_config as CC
    return CC.config.get_cache_dir()
