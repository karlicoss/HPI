'''
A helper to make warnings a bit more visible.
TODO ideally would be great to replace with some existing solution, or find a better way,
since who looks at the terminal output?
E.g. would be nice to propagate the warnings in the UI (it's even a subclass of Exception!)
'''

from __future__ import annotations

import sys
import warnings
from typing import TYPE_CHECKING

import click


def _colorize(x: str, color: str | None = None) -> str:
    if color is None:
        return x

    if not sys.stderr.isatty():
        return x
    # click handles importing/initializing colorama if necessary
    # on windows it installs it if necessary
    # on linux/mac, it manually handles ANSI without needing termcolor
    return click.style(x, fg=color)


def _warn(message: str, *args, color: str | None = None, **kwargs) -> None:
    stacklevel = kwargs.get('stacklevel', 1)
    kwargs['stacklevel'] = stacklevel + 2  # +1 for this function, +1 for medium/high wrapper
    warnings.warn(_colorize(message, color=color), *args, **kwargs)  # noqa: B028


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


if not TYPE_CHECKING:
    from .compat import deprecated

    @deprecated('use warnings.warn directly instead')
    def warn(*args, **kwargs):
        import warnings

        return warnings.warn(*args, **kwargs)  # noqa: B028
