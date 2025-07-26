from __future__ import annotations

import logging
import os
import sys
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING, Union


def test() -> None:
    from typing import Callable

    M: Callable[[str], None] = lambda s: print(s, file=sys.stderr)

    ## prepare exception for later
    try:
        None.whatever  # type: ignore[attr-defined]  # noqa: B018
    except Exception as e:
        ex = e
    ##

    M("   Logging module's defaults are not great:")
    l = logging.getLogger('default_logger')
    l.error("For example, this should be logged as error. But it's not even formatted properly, doesn't have logger name or level")

    M("\n   The reason is that you need to remember to call basicConfig() first. Let's do it now:")
    logging.basicConfig()
    l.error("OK, this is better. But the default format kinda sucks, I prefer having timestamps and the file/line number")

    M("\n   Also exception logging is kinda lame, doesn't print traceback by default unless you remember to pass exc_info:")
    l.exception(ex)  # type: ignore[possibly-undefined]

    M("\n\n    With make_logger you get a reasonable logging format, colours (via colorlog library) and other neat things:")

    ll = make_logger('test')  # No need for basicConfig!
    ll.info("default level is INFO")
    ll.debug("... so this shouldn't be displayed")
    ll.warning("warnings are easy to spot!")

    M("\n    Exceptions print traceback by default now:")
    ll.exception(ex)

    M("\n    You can (and should) use it via regular logging.getLogger after that, e.g. let's set logging level to DEBUG now")
    logging.getLogger('test').setLevel(logging.DEBUG)
    ll.debug("... now debug messages are also displayed")


DEFAULT_LEVEL = 'INFO'
FORMAT = '{start}[%(levelname)-7s %(asctime)s %(name)s %(filename)s:%(lineno)-4d]{end} %(message)s'
FORMAT_NOCOLOR = FORMAT.format(start='', end='')


Level = int
LevelIsh = Union[Level, str, None]


def mklevel(level: LevelIsh) -> Level:
    if level is None:
        return logging.NOTSET
    if isinstance(level, int):
        return level
    return getattr(logging, level.upper())


def get_collapse_level() -> Level | None:
    # TODO not sure if should be specific to logger name?
    cl = os.environ.get('LOGGING_COLLAPSE', None)
    if cl is not None:
        return mklevel(cl)
    # legacy name, maybe deprecate?
    cl = os.environ.get('COLLAPSE_DEBUG_LOGS', None)
    if cl is not None:
        return logging.DEBUG
    return None


def get_env_level(name: str) -> Level | None:
    PREFIX = 'LOGGING_LEVEL_'  # e.g. LOGGING_LEVEL_my_hypothesis=debug
    # shell doesn't allow using dots in var names without escaping, so also support underscore syntax
    lvl = os.environ.get(PREFIX + name, None) or os.environ.get(PREFIX + name.replace('.', '_'), None)
    if lvl is not None:
        return mklevel(lvl)
    # if LOGGING_LEVEL_HPI is set, use that. This should override anything the module may set as its default
    # this is also set when the user passes the --debug flag in the CLI
    #
    # check after LOGGING_LEVEL_ prefix since that is more specific
    if 'LOGGING_LEVEL_HPI' in os.environ:
        return mklevel(os.environ['LOGGING_LEVEL_HPI'])
    # legacy name, for backwards compatibility
    if 'HPI_LOGS' in os.environ:
        from my.core.warnings import medium

        medium('The HPI_LOGS environment variable is deprecated, use LOGGING_LEVEL_HPI instead')

        return mklevel(os.environ['HPI_LOGS'])
    return None


def setup_logger(logger: str | logging.Logger, *, level: LevelIsh = None) -> None:
    """
    Wrapper to simplify logging setup.
    """
    if isinstance(logger, str):
        logger = logging.getLogger(logger)

    if level is None:
        level = DEFAULT_LEVEL

    # env level always takes precedence
    env_level = get_env_level(logger.name)
    if env_level is not None:
        lvl = env_level
    else:
        lvl = mklevel(level)

    if logger.level == logging.NOTSET:
        # if it's already set, the user requested a different logging level, let's respect that
        logger.setLevel(lvl)

    _setup_handlers_and_formatters(name=logger.name)


# cached since this should only be done once per logger instance
@lru_cache(None)
def _setup_handlers_and_formatters(name: str) -> None:
    logger = logging.getLogger(name)

    logger.addFilter(AddExceptionTraceback())

    collapse_level = get_collapse_level()
    if collapse_level is None or not sys.stderr.isatty():
        handler = logging.StreamHandler()
    else:
        handler = CollapseLogsHandler(maxlevel=collapse_level)

    # default level for handler is NOTSET, which will make it process all messages
    # we rely on the logger to actually accept/reject log msgs
    logger.addHandler(handler)

    # this attribute is set to True by default, which causes log entries to be passed to root logger (e.g. if you call basicConfig beforehand)
    # even if log entry is handled by this logger ... not sure what's the point of this behaviour??
    logger.propagate = False

    try:
        # try colorlog first, so user gets nice colored logs
        import colorlog
    except ModuleNotFoundError:
        warnings.warn("You might want to 'pip install colorlog' for nice colored logs", stacklevel=1)
        formatter = logging.Formatter(FORMAT_NOCOLOR)
    else:
        # log_color/reset are specific to colorlog
        FORMAT_COLOR = FORMAT.format(start='%(log_color)s', end='%(reset)s')
        # colorlog should detect tty in principle, but doesn't handle everything for some reason
        # see https://github.com/borntyping/python-colorlog/issues/71
        if handler.stream.isatty():
            formatter = colorlog.ColoredFormatter(FORMAT_COLOR)
        else:
            formatter = logging.Formatter(FORMAT_NOCOLOR)

    handler.setFormatter(formatter)


# by default, logging.exception isn't logging traceback unless called inside of the exception handler
# which is a bit annoying since we have to pass exc_info explicitly
# also see https://stackoverflow.com/questions/75121925/why-doesnt-python-logging-exception-method-log-traceback-by-default
# todo also amend by post about defensive error handling?
class AddExceptionTraceback(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname == 'ERROR':
            exc = record.msg
            if isinstance(exc, BaseException):
                if record.exc_info is None or record.exc_info == (None, None, None):
                    exc_info = (type(exc), exc, exc.__traceback__)
                    record.exc_info = exc_info
        return True


# todo also save full log in a file?
class CollapseLogsHandler(logging.StreamHandler):
    '''
    Collapses subsequent debug log lines and redraws on the same line.
    Hopefully this gives both a sense of progress and doesn't clutter the terminal as much?
    '''

    last: bool = False

    maxlevel: Level = logging.DEBUG  # everything with less or equal level will be collapsed

    def __init__(self, *args, maxlevel: Level, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.maxlevel = maxlevel

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            cur = record.levelno <= self.maxlevel and '\n' not in msg
            if cur:
                if self.last:
                    self.stream.write('\033[K' + '\r')  # clear line + return carriage
            else:
                if self.last:
                    self.stream.write('\n')  # clean up after the last line
            self.last = cur
            columns, _ = os.get_terminal_size(0)
            # ugh. the columns thing is meh. dunno I guess ultimately need curses for that
            # TODO also would be cool to have a terminal post-processor? kinda like tail but aware of logging keywords (INFO/DEBUG/etc)
            self.stream.write(msg + ' ' * max(0, columns - len(msg)) + ('' if cur else '\n'))
            self.flush()
        except:
            self.handleError(record)


def make_logger(name: str, *, level: LevelIsh = None) -> logging.Logger:
    logger = logging.getLogger(name)
    setup_logger(logger, level=level)
    return logger


# ughh. hacky way to have a single enlighten instance per interpreter, so it can be shared between modules
# not sure about this. I guess this should definitely be behind some flag
# OK, when stdout is not a tty, enlighten doesn't log anything, good
def get_enlighten():
    # TODO could add env variable to disable enlighten for a module?
    from unittest.mock import (
        Mock,  # Mock to return stub so cients don't have to think about it
    )

    # for now hidden behind the flag since it's a little experimental
    if os.environ.get('ENLIGHTEN_ENABLE', None) is None:
        return Mock()

    try:
        import enlighten  # type: ignore[import-untyped]
    except ModuleNotFoundError:
        warnings.warn("You might want to 'pip install enlighten' for a nice progress bar", stacklevel=1)

        return Mock()

    # dirty, but otherwise a bit unclear how to share enlighten manager between packages that call each other
    instance = getattr(enlighten, 'INSTANCE', None)
    if instance is not None:
        return instance
    instance = enlighten.get_manager()
    setattr(enlighten, 'INSTANCE', instance)
    return instance


if __name__ == '__main__':
    test()


## legacy/deprecated methods for backwards compatibility
if not TYPE_CHECKING:
    from .compat import deprecated

    @deprecated('use make_logger instead')
    def LazyLogger(*args, **kwargs):
        return make_logger(*args, **kwargs)

    @deprecated('use make_logger instead')
    def logger(*args, **kwargs):
        return make_logger(*args, **kwargs)


##
