"""
A helper to allow configuring the modules dynamically.

Usage:

  from my.cfg import config

After that, you can set config attributes:

  from types import SimpleNamespace
  config.twitter = SimpleNamespace(
      export_path='/path/to/twitter/exports',
  )
"""
# todo why do we bring this into scope? don't remember..
import my.config as config


def set_repo(name: str, repo):
    from .core.init import assign_module
    from . common import import_from

    module = import_from(repo, name)
    assign_module('my.config.repos', name, module)


# TODO set_repo is still useful, but perhaps move this thing away to core?
