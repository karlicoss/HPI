"""
A helper to allow configuring the modules dynamically.

Usage:

  from my.cfg import config

After that, you can set config attributes:

  class user_config:
      export_path = '/path/to/twitter/exports'
  config.twitter = user_config
"""
# TODO do I really need it?

# todo why do we bring this into scope? don't remember..
import my.config as config

from .core import __NOT_HPI_MODULE__
