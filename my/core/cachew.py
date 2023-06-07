from .common import assert_subpackage; assert_subpackage(__name__)

from contextlib import contextmanager
import logging
from pathlib import Path
import sys
from typing import Optional, Iterator, cast, TYPE_CHECKING, TypeVar, Callable, overload, Union, Any, Type
import warnings

import appdirs

PathIsh = Union[str, Path]  # avoid circular import from .common


def disable_cachew() -> None:
    try:
        import cachew  # noqa: F401 # unused, it's fine
    except ImportError:
        # nothing to disable
        return

    from cachew import settings

    settings.ENABLE = False


@contextmanager
def disabled_cachew() -> Iterator[None]:
    try:
        import cachew  # noqa: F401 # unused, it's fine
    except ImportError:
        # nothing to disable
        yield
        return
    from cachew.extra import disabled_cachew

    with disabled_cachew():
        yield


def _appdirs_cache_dir() -> Path:
    cd = Path(appdirs.user_cache_dir('my'))
    cd.mkdir(exist_ok=True, parents=True)
    return cd


_CACHE_DIR_NONE_HACK = Path('/tmp/hpi/cachew_none_hack')


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
        cdir = _CACHE_DIR_NONE_HACK
    else:
        cdir = cdir_

    return cdir if sp is None else cdir / sp


"""See core.cachew.cache_dir for the explanation"""


_cache_path_dflt = cast(str, object())


# TODO I don't really like 'mcachew', just 'cache' would be better... maybe?
# todo ugh. I think it needs @doublewrap, otherwise @mcachew without args doesn't work
# but it's a bit problematic.. doublewrap works by defecting if the first arg is callable
# but here cache_path can also be a callable (for lazy/dynamic path)... so unclear how to detect this
def _mcachew_impl(cache_path=_cache_path_dflt, **kwargs):
    """
    Stands for 'Maybe cachew'.
    Defensive wrapper around @cachew to make it an optional dependency.
    """
    if cache_path is _cache_path_dflt:
        # wasn't specified... so we need to use cache_dir
        cache_path = cache_dir()

    if isinstance(cache_path, (str, Path)):
        try:
            # check that it starts with 'hack' path
            Path(cache_path).relative_to(_CACHE_DIR_NONE_HACK)
        except:  # noqa: E722 bare except
            pass  # no action needed, doesn't start with 'hack' string
        else:
            # todo show warning? tbh unclear how to detect when user stopped using 'old' way and using suffix instead?
            # if it does, means that user wanted to disable cache
            cache_path = None
    try:
        import cachew
    except ModuleNotFoundError:
        warnings.warn('cachew library not found. You might want to install it to speed things up. See https://github.com/karlicoss/cachew')
        return lambda orig_func: orig_func
    else:
        kwargs['cache_path'] = cache_path
        return cachew.cachew(**kwargs)


if TYPE_CHECKING:
    R = TypeVar('R')
    if sys.version_info[:2] >= (3, 10):
        from typing import ParamSpec
    else:
        from typing_extensions import ParamSpec
    P = ParamSpec('P')
    CC = Callable[P, R]  # need to give it a name, if inlined into bound=, mypy runs in a bug
    PathProvider = Union[PathIsh, Callable[P, PathIsh]]
    # NOTE: in cachew, HashFunction type returns str
    # however in practice, cachew alwasy calls str for its result
    # so perhaps better to switch it to Any in cachew as well
    HashFunction = Callable[P, Any]

    F = TypeVar('F', bound=Callable)

    # we need two versions due to @doublewrap
    # this is when we just annotate as @cachew without any args
    @overload  # type: ignore[no-overload-impl]
    def mcachew(fun: F) -> F:
        ...

    @overload
    def mcachew(
        cache_path: Optional[PathProvider] = ...,
        *,
        force_file: bool = ...,
        cls: Optional[Type] = ...,
        depends_on: HashFunction = ...,
        logger: Optional[logging.Logger] = ...,
        chunk_by: int = ...,
        synthetic_key: Optional[str] = ...,
    ) -> Callable[[F], F]:
        ...

else:
    mcachew = _mcachew_impl
