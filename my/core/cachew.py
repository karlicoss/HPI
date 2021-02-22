from .common import assert_subpackage; assert_subpackage(__name__)

from contextlib import contextmanager
from pathlib import Path
from typing import Optional

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


from . import PathIsh
def cache_dir(suffix: Optional[PathIsh] = None) -> Path:
    from . import core_config as CC
    cdir_ = CC.config.get_cache_dir()

    sp: Optional[Path] = None
    if suffix is not None:
        sp = Path(suffix)
        # guess if you do need absolute, better path it directly instead of as suffix?
        assert not sp.is_absolute(), sp

    # ok, so ideally we could just return cdir_ / sp
    # however, this function was at first used without the suffix, e.g. cache_dir() / 'some_dir'
    # but now cache_dir setting can also be None which means 'disable cache'
    # changing return type to Optional means that it will break for existing users even if the cache isn't used
    # it's kinda wrong.. so we use dummy path (_CACHE_DIR_NONE_HACK), and then strip it away in core.common.mcachew
    # this logic is tested via test_cachew_dir_none

    if cdir_ is None:
        from .common import _CACHE_DIR_NONE_HACK
        cdir = _CACHE_DIR_NONE_HACK
    else:
        cdir = cdir_

    return cdir if sp is None else cdir / sp
