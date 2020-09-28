'''
Bindings for the 'core' HPI configuration
'''
import re
from typing import Sequence, Optional

from .common import PathIsh

try:
    # FIXME support legacy 'common'?
    from my.config import core as user_config # type: ignore[attr-defined]
except Exception as e:
    # make it defensive, because it's pretty commonly used and would be annoying if it breaks hpi doctor etc.
    # this way it'll at least use the defaults
    # TODO add high warning
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
                # only enabled the specifid modules
                return matches(enabled)
            else:
                # ok, this means the config is inconsistent. better fallback onto the 'enable everything', then the user will notice?
                # todo add medium warning?
                return True


from .cfg import make_config
config = make_config(Config)
