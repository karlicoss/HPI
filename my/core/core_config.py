'''
Bindings for the 'core' HPI configuration
'''
import re
from typing import Sequence, Optional

from .common import PathIsh
from . import warnings

try:
    from my.config import core as user_config # type: ignore[attr-defined]
except Exception as e:
    try:
        from my.config import common as user_config # type: ignore[attr-defined, assignment, misc]
        warnings.high("'common' config section is deprecated. Please rename it to 'core'.")
    except Exception as e2:
        # make it defensive, because it's pretty commonly used and would be annoying if it breaks hpi doctor etc.
        # this way it'll at least use the defaults
        # todo actually not sure if needs a warning? Perhaps it's okay without it, because the defaults are reasonable enough
        user_config = object # type: ignore[assignment, misc]


from dataclasses import dataclass
@dataclass
class Config(user_config):
    # TODO if attr is set _and_ it's none, disable cache?
    # todo or empty string?
    # I guess flip the switch at some point when I'm confident in cachew
    cache_dir: Optional[PathIsh] = None # FIXME use appdirs cache dir or something

    # list of regexes/globs
    # None means 'rely on disabled_modules'
    enabled_modules : Optional[Sequence[str]] = None

    # list of regexes/globs
    # None means 'rely on enabled_modules'
    disabled_modules: Optional[Sequence[str]] = None


    def _is_module_active(self, module: str) -> Optional[bool]:
        # None means the config doesn't specify anything
        # todo might be nice to return the 'reason' too? e.g. which option has matched
        def matches(specs: Sequence[str]) -> Optional[str]:
            for spec in specs:
                # not sure because . (packages separate) matches anything, but I guess unlikely to clash
                if re.match(spec, module):
                    return spec
            return None

        enabled  = self.enabled_modules
        disabled = self.disabled_modules
        on  = matches(self.enabled_modules  or [])
        off = matches(self.disabled_modules or [])

        if on is None:
            if off is None:
                # user is indifferent
                return None
            else:
                return False
        else: # not None
            if off is None:
                return True
            else: # not None
                # fallback onto the 'enable everything', then the user will notice
                warnings.medium(f"[module]: conflicting regexes '{on}' and '{off}' are set in the config. Please only use one of them.")
                return True


from .cfg import make_config
config = make_config(Config)


### tests start
from typing import Iterator, Any
from contextlib import contextmanager as ctx
@ctx
def _reset_config() -> Iterator[Config]:
    # todo maybe have this decorator for the whole of my.config?
    from .cfg import override_config
    with override_config(config) as cc:
        cc.enabled_modules  = None
        cc.disabled_modules = None
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
        assert     cc._is_module_active('my.whatever'     ) is True
        assert     cc._is_module_active('my.core'         ) is None
        assert not cc._is_module_active('my.body.exercise') is True

    with reset() as cc:
        # if both are set, enable all
        cc.disabled_modules = ['my.body.*']
        cc.enabled_modules =  ['my.body.exercise']
        assert cc._is_module_active('my.whatever'     ) is None
        assert cc._is_module_active('my.core'         ) is None
        with pytest.warns(UserWarning, match=r"conflicting regexes") as record_warnings:
            assert cc._is_module_active("my.body.exercise") is True
        assert len(record_warnings) == 1

### tests end
