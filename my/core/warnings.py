'''
A helper to make warnings a bit more visible.
TODO ideally would be great to replace with some existing solution, or find a better way,
since who looks at the terminal output?
E.g. would be nice to propagate the warnings in the UI (it's even a subclass of Exception!)
'''

import sys
from typing import Optional
import warnings

import click


# just bring in the scope of this module for convenience
from warnings import warn

def _colorize(x: str, color: Optional[str]=None) -> str:
    if color is None:
        return x

    if not sys.stdout.isatty():
        return x
    # click handles importing/initializing colorama if necessary
    # on windows it installs it if necessary
    # on linux/mac, it manually handles ANSI without needing termcolor
    return click.style(x, fg=color)


def _warn(message: str, *args, color: Optional[str]=None, **kwargs) -> None:
    stacklevel = kwargs.get('stacklevel', 1)
    kwargs['stacklevel'] = stacklevel + 2 # +1 for this function, +1 for medium/high wrapper
    warnings.warn(_colorize(message, color=color), *args, **kwargs)


def low(message: str, *args, **kwargs) -> None:
    # kwargs['color'] = 'grey' # eh, grey is way too pale
    _warn(message, *args, **kwargs)


def medium(message: str, *args, **kwargs) -> None:
    kwargs['color'] = 'yellow'
    _warn(message, *args, **kwargs)


def high(message: str, *args, **kwargs) -> None:
    '''
    Meant for deprecations, i.e. things that better get some user attention
    '''
    kwargs['color'] = 'red'
    _warn(message, *args, **kwargs)
