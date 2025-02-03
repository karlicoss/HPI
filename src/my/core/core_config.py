'''
Bindings for the 'core' HPI configuration
'''

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import warnings

try:
    from my.config import core as user_config  # type: ignore[attr-defined]
except Exception as _e:
    try:
        from my.config import common as user_config  # type: ignore[attr-defined]

        warnings.high("'common' config section is deprecated. Please rename it to 'core'.")
    except Exception as _e2:
        # make it defensive, because it's pretty commonly used and would be annoying if it breaks hpi doctor etc.
        # this way it'll at least use the defaults
        # todo actually not sure if needs a warning? Perhaps it's okay without it, because the defaults are reasonable enough
        user_config = object


_HPI_CACHE_DIR_DEFAULT = ''


@dataclass
class Config(user_config):
    '''
    Config for the HPI itself.
    To override, add to your config file something like

    class config:
        cache_dir = '/your/custom/cache/path'
    '''

    cache_dir: Path | str | None = _HPI_CACHE_DIR_DEFAULT
    '''
    Base directory for cachew.
    - if None             , means cache is disabled
    - if '' (empty string), use user cache dir (see https://github.com/tox-dev/platformdirs?tab=readme-ov-file#example-output for more info). This is the default.
    - otherwise           , use the specified directory as base cache directory

    NOTE: you shouldn't use this attribute in HPI modules directly, use Config.get_cache_dir()/cachew.cache_dir() instead
    '''

    tmp_dir: Path | str | None = None
    '''
    Path to a temporary directory.
    This can be used temporarily while extracting zipfiles etc...
    - if None             , uses default determined by tempfile.gettempdir + 'HPI'
    - otherwise           , use the specified directory as the base temporary directory
    '''

    enabled_modules: Sequence[str] | None = None
    '''
    list of regexes/globs
    - None means 'rely on disabled_modules'
    '''

    disabled_modules: Sequence[str] | None = None
    '''
    list of regexes/globs
    - None means 'rely on enabled_modules'
    '''

    def get_cache_dir(self) -> Path | None:
        cdir = self.cache_dir
        if cdir is None:
            return None
        if cdir == _HPI_CACHE_DIR_DEFAULT:
            from .cachew import _hpi_cache_dir

            return _hpi_cache_dir()
        else:
            return Path(cdir).expanduser()

    def get_tmp_dir(self) -> Path:
        tdir: Path | str | None = self.tmp_dir
        tpath: Path
        # use tempfile if unset
        if tdir is None:
            import tempfile

            tpath = Path(tempfile.gettempdir()) / 'HPI'
        else:
            tpath = Path(tdir)
        tpath = tpath.expanduser()
        tpath.mkdir(parents=True, exist_ok=True)
        return tpath

    def _is_module_active(self, module: str) -> bool | None:
        # None means the config doesn't specify anything
        # todo might be nice to return the 'reason' too? e.g. which option has matched
        def matches(specs: Sequence[str]) -> str | None:
            for spec in specs:
                # not sure because . (packages separate) matches anything, but I guess unlikely to clash
                if re.match(spec, module):
                    return spec
            return None

        on  = matches(self.enabled_modules  or [])
        off = matches(self.disabled_modules or [])

        if on is None:
            if off is None:
                # user is indifferent
                return None
            else:
                return False
        else:  # not None
            if off is None:
                return True
            else:  # not None
                # fallback onto the 'enable everything', then the user will notice
                warnings.medium(f"[module]: conflicting regexes '{on}' and '{off}' are set in the config. Please only use one of them.")
                return True


from .cfg import make_config

config = make_config(Config)


### tests start
from collections.abc import Iterator
from contextlib import contextmanager as ctx


@ctx
def _reset_config() -> Iterator[Config]:
    # todo maybe have this decorator for the whole of my.config?
    from .cfg import _override_config
    with _override_config(config) as cc:
        cc.enabled_modules  = None
        cc.disabled_modules = None
        cc.cache_dir        = None
        yield cc


def test_active_modules() -> None:
    import pytest

    reset = _reset_config

    with reset() as cc:
        assert cc._is_module_active('my.whatever'     ) is None
        assert cc._is_module_active('my.core'         ) is None
        assert cc._is_module_active('my.body.exercise') is None

    with reset() as cc:
        cc.enabled_modules  = ['my.whatever']
        cc.disabled_modules = ['my.body.*']
        assert cc._is_module_active('my.whatever'     ) is True
        assert cc._is_module_active('my.core'         ) is None
        assert cc._is_module_active('my.body.exercise') is False

    with reset() as cc:
        # if both are set, enable all
        cc.disabled_modules = ['my.body.*']
        cc.enabled_modules  = ['my.body.exercise']
        assert cc._is_module_active('my.whatever'     ) is None
        assert cc._is_module_active('my.core'         ) is None
        with pytest.warns(UserWarning, match=r"conflicting regexes") as record_warnings:
            assert cc._is_module_active("my.body.exercise") is True
        assert len(record_warnings) == 1


### tests end
