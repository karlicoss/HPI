from dataclasses import dataclass


# 'bare' config, no typing annotations even
# current_impl  : works both mypy and runtime
#   if we comment out export_path, mypy DOES NOT fail (bad!)
# via_dataclass : FAILS both mypy and runtime
# via_properties: works both mypy and runtime
#   if we comment out export_path, mypy fails (good!)
#   src/pkg/via_properties.py:32:12:32:28: error: Cannot instantiate abstract class "combined_config" with abstract attribute "export_path"  [abstract]
#           return combined_config()
class module_config_1:
    custom_setting = 'adhoc setting'
    export_path = '/path/to/data'


# config defined with @dataclass annotation
# current_impl  : works in runtime
#   mypy DOES NOT pass
#    seems like it doesn't like that non-default attributes (export_path: str) in module config
#    are following default attributes (export_path in this config)
# via_dataclass : works both mypy and runtime
#   if we comment out export_path, mypy fails (good!)
#   src/pkg/via_dataclass.py:56:12:56:28: error: Missing positional argument "export_path" in call to "combined_config"  [call-arg]
#       return combined_config()
# via_properties: works both mypy and runtime
#   if we comment out export_path, mypy fails (good!)
#   same error as above

@dataclass
class module_config_2:
    custom_setting: str = 'adhoc setting'
    export_path: str = '/path/to/data'


# NOTE: ok, if a config attrubute happened to be a classproperty, then it fails mypy
#   but it still works in runtime, which is good, easy to migrate if necessary


# mixed style config, some attributes are defined via property
# this is quite useful if you want to defer some computations from config import time
# current_impl  : works both mypy and runtime
#   if we comment out export_path, mypy DOES NOT fail (bad!)
# via_dataclass : FAILS both mypy and runtime
# via_properties: works both mypy and runtime
#   if we comment out export_path, mypy fails (good!)
#   same error as above
class module_config_3:
    custom_setting: str = 'adhoc setting'

    @property
    def export_path(self) -> str:
        return '/path/to/data'


# same mixed style as above, but also a @dataclass annotation
# via_dataclass: FAILS both mypy and runtime
#   src/pkg/via_dataclass.py: note: In function "make_config":
#   src/pkg/via_dataclass.py:53:5:54:12: error: Definition of "export_path" in base class "module_config" is incompatible with definition in base class "config"  [misc]
#           class combined_config(user_config, config):
#           ^
#   src/pkg/via_dataclass.py:56:12:56:28: error: Missing positional argument "export_path" in call to "combined_config"  [call-arg]
#           return combined_config()
#                  ^~~~~~~~~~~~~~~~~
# via_properties: works both mypy and runtime
#   if we comment out export_path, mypy fails (good!)
#   same error as above
@dataclass
class module_config_4:
    custom_setting: str = 'adhoc setting'

    @classproperty
    def export_path(self) -> str:
        return '/path/to/data'
