#!/usr/bin/env python3
'''
Default logger is a bit meh, see 'test'/run this file for a demo
TODO name 'klogging' to avoid possible conflict with default 'logging' module
TODO shit. too late already? maybe use fallback & deprecate
'''


def test() -> None:
    from typing import Callable
    import logging
    import sys

    M: Callable[[str], None] = lambda s: print(s, file=sys.stderr)

    M("   Logging module's defaults are not great...'")
    l = logging.getLogger('test_logger')
    # todo why is mypy unhappy about these???
    l.error("For example, this should be logged as error. But it's not even formatted properly, doesn't have logger name or level")

    M("   The reason is that you need to remember to call basicConfig() first")
    l.error("OK, this is better. But the default format kinda sucks, I prefer having timestamps and the file/line number")

    M("")
    M("    With LazyLogger you get a reasonable logging format, colours and other neat things")

    ll = LazyLogger('test')  # No need for basicConfig!
    ll.info("default level is INFO")
    ll.debug(".. so this shouldn't be displayed")
    ll.warning("warnings are easy to spot!")
    ll.exception(RuntimeError("exceptions as well"))


import logging
from typing import Union, Optional
import os

Level = int
LevelIsh = Optional[Union[Level, str]]


def mklevel(level: LevelIsh) -> Level:
    # todo put in some global file, like envvars.py
    glevel = os.environ.get('HPI_LOGS', None)
    if glevel is not None:
        level = glevel
    if level is None:
        return logging.NOTSET
    if isinstance(level, int):
        return level
    return getattr(logging, level.upper())


FORMAT = '{start}[%(levelname)-7s %(asctime)s %(name)s %(filename)s:%(lineno)d]{end} %(message)s'
FORMAT_COLOR   = FORMAT.format(start='%(color)s', end='%(end_color)s')
FORMAT_NOCOLOR = FORMAT.format(start='', end='')
DATEFMT = '%Y-%m-%d %H:%M:%S'


def setup_logger(logger: logging.Logger, level: LevelIsh) -> None:
    lvl = mklevel(level)
    try:
        import logzero  # type: ignore[import]
    except ModuleNotFoundError:
        import warnings

        warnings.warn("You might want to install 'logzero' for nice colored logs!")
        logger.setLevel(lvl)
        h = logging.StreamHandler()
        h.setLevel(lvl)
        h.setFormatter(logging.Formatter(fmt=FORMAT_NOCOLOR, datefmt=DATEFMT))
        logger.addHandler(h)
        logger.propagate = False  # ugh. otherwise it duplicates log messages? not sure about it..
    else:
        formatter = logzero.LogFormatter(
            fmt=FORMAT_COLOR,
            datefmt=DATEFMT,
        )
        logzero.setup_logger(logger.name, level=lvl, formatter=formatter)


class LazyLogger(logging.Logger):
    def __new__(cls, name: str, level: LevelIsh = 'INFO') -> 'LazyLogger':
        logger = logging.getLogger(name)
        # this is called prior to all _log calls so makes sense to do it here?
        def isEnabledFor_lazyinit(*args, logger=logger, orig=logger.isEnabledFor, **kwargs):
            att = 'lazylogger_init_done'
            if not getattr(logger, att, False):  # init once, if necessary
                setup_logger(logger, level=level)
                setattr(logger, att, True)
            return orig(*args, **kwargs)

        logger.isEnabledFor = isEnabledFor_lazyinit  # type: ignore[assignment]
        return logger  # type: ignore[return-value]


if __name__ == '__main__':
    test()
