"""
A helper to allow configuring the modules dynamically.

Usage:

  from my.cfg import config

After that, you can set config attributes:

  class user_config:
      export_path = '/path/to/twitter/exports'
  config.twitter = user_config
"""
# todo why do we bring this into scope? don't remember..
import my.config as config


from pathlib import Path
from typing import Union
def set_repo(name: str, repo: Union[Path, str]) -> None:
    from .core.init import assign_module
    from . common import import_from

    r = Path(repo)
    module = import_from(r.parent, name)
    assign_module('my.config.repos', name, module)


# TODO set_repo is still useful, but perhaps move this thing away to core?

# TODO ok, I need to get rid of this, better to rely on regular imports

from .core import __NOT_HPI_MODULE__
