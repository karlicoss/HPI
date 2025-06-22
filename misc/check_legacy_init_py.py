#!/usr/bin/env python3
# NOTE: prerequisites for this test:
# fbmessengerexport installed
# config configured (can set it to '' though)

from pathlib import Path
from subprocess import PIPE, Popen, run
from tempfile import TemporaryDirectory

import logzero  # type: ignore[import]

logger = logzero.logger


MSG = 'my.fbmessenger is DEPRECATED'

def expect(*cmd: str, should_warn: bool=True) -> None:
    res = run(cmd, stderr=PIPE, check=False)
    errb = res.stderr; assert errb is not None
    err = errb.decode('utf8')
    if should_warn:
        assert MSG     in err, res
    else:
        assert MSG not in err, res
    assert res.returncode == 0, res


def _check(*cmd: str, should_warn: bool, run_as_cmd: bool=True) -> None:
    expecter = lambda *cmd: expect(*cmd, should_warn=should_warn)
    if cmd[0] == '-c':
        [_, code] = cmd
        if run_as_cmd:
            expecter('python3', '-c', code)
        # check as a script
        with TemporaryDirectory() as tdir:
            script = Path(tdir) / 'script.py'
            script.write_text(code)
            expecter('python3', str(script))
    else:
        expecter('python3', *cmd)
    what = 'warns' if should_warn else '     ' # meh
    logger.info(f"PASSED: {what}: {cmd!r}")


def check_warn(*cmd: str, **kwargs) -> None:
    _check(*cmd, should_warn=True, **kwargs)

def check_ok(*cmd: str, **kwargs) -> None:
    _check(*cmd, should_warn=False, **kwargs)


# NOTE these three are actually sort of OK, they are allowed when it's a proper namespace package with all.py etc.
# but more likely it means legacy behaviour or just misusing the package?
# worst case it's just a warning I guess
check_warn('-c', 'from   my import fbmessenger')
check_warn('-c', 'import my.fbmessenger')
check_warn('-c', 'from   my.fbmessenger import *')

# note: dump_chat_history should really be deprecated, but it's a quick way to check we actually fell back to fbmessenger/export.py
# NOTE: this is the most common legacy usecase
check_warn('-c', 'from   my.fbmessenger import messages, dump_chat_history')
check_warn('-m', 'my.core', 'query' , 'my.fbmessenger.messages', '-o', 'pprint', '--limit=10')
check_warn('-m', 'my.core', 'doctor', 'my.fbmessenger')
check_warn('-m', 'my.core', 'module', 'requires', 'my.fbmessenger')

# todo kinda annoying it doesn't work when executed as -c (but does as script!)
# presumably because doesn't have proper line number information?
# either way, it'a a bit of a corner case, the script behaviour is more important
check_ok  ('-c', 'from   my.fbmessenger import export', run_as_cmd=False)
check_ok  ('-c', 'import my.fbmessenger.export')
check_ok  ('-c', 'from   my.fbmessenger.export import *')
check_ok  ('-c', 'from my.fbmessenger.export import messages, dump_chat_history')
check_ok  ('-m', 'my.core', 'query' , 'my.fbmessenger.export.messages', '-o', 'pprint', '--limit=10')
check_ok  ('-m', 'my.core', 'doctor', 'my.fbmessenger.export')
check_ok  ('-m', 'my.core', 'module', 'requires', 'my.fbmessenger.export')

# NOTE:
# to check that overlays work, run something like
# PYTHONPATH=misc/overlay_for_init_py_test/  hpi query my.fbmessenger.all.messages -s -o pprint --limit=10
# you should see 1, 2, 3 from mixin.py
# TODO would be nice to add an automated test for this

# TODO with reddit, currently these don't work properly at all
# only when imported from scripts etc?
