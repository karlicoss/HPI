"""
Feel free to remove this if you don't need it/add your own custom settings and use them
"""

from my.core import Paths

class hypothesis:
    # expects outputs from https://github.com/karlicoss/hypexport
    # (it's just the standard Hypothes.is export format)
    export_path: Paths = '/path/to/hypothesis/data'

class instapaper:
    export_path: Paths = ''
