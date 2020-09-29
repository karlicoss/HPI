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


    def is_module_active(self, module: str) -> bool:
        # todo might be nice to return the 'reason' too? e.g. which option has matched
        should_enable  = None
        should_disable = None
        def matches(specs: Sequence[str]) -> bool:
            for spec in specs:
                # not sure because . (packages separate) matches anything, but I guess unlikely to clash
                if re.match(spec, module):
                    return True
            return False

        enabled  = self.enabled_modules
        disabled = self.disabled_modules
        if enabled is None:
            if disabled is None:
                # by default, enable everything? not sure
                return True
            else:
                # only disable the specified modules
                return not matches(disabled)
        else:
            if disabled is None:
                # only enable the specified modules
                return matches(enabled)
            else:
                # ok, this means the config is inconsistent. better fallback onto the 'enable everything', then the user will notice?
                warnings.medium("Both 'enabled_modules' and 'disabled_modules' are set in the config. Please only use one of them.")
                return True


from .cfg import make_config
config = make_config(Config)


### tests start

def test_active_modules() -> None:
    # todo maybe have this decorator for the whole of my.config?
    from contextlib import contextmanager as ctx
    @ctx
    def reset():
        from .cfg import override_config
        with override_config(config) as cc:
            cc.enabled_modules  = None
            cc.disabled_modules = None
            yield cc

    with reset() as cc:
        assert cc.is_module_active('my.whatever')
        assert cc.is_module_active('my.core'    )
        assert cc.is_module_active('my.body.exercise')

    with reset() as cc:
        cc.disabled_modules = ['my.body.*']
        assert cc.is_module_active('my.whatever')
        assert cc.is_module_active('my.core'    )
        assert not cc.is_module_active('my.body.exercise')

    with reset() as cc:
        cc.enabled_modules = ['my.whatever']
        assert cc.is_module_active('my.whatever')
        assert not cc.is_module_active('my.core'    )
        assert not cc.is_module_active('my.body.exercise')

    with reset() as cc:
        # if both are set, enable all
        cc.disabled_modules = ['my.body.*']
        cc.enabled_modules = ['my.whatever']
        assert cc.is_module_active('my.whatever')
        assert cc.is_module_active('my.core'    )
        assert cc.is_module_active('my.body.exercise')
        # todo suppress warnings during the tests?

### tests end
