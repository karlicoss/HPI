import os
from pathlib import Path
import sys
from subprocess import check_call, run, PIPE
from typing import Optional, Sequence, Iterable
import importlib
import traceback

from . import LazyLogger

log = LazyLogger('HPI cli')


import functools
@functools.lru_cache()
def mypy_cmd() -> Optional[Sequence[str]]:
    try:
        # preferably, use mypy from current python env
        import mypy
        return ['python3', '-m', 'mypy']
    except ImportError:
        pass
    # ok, not ideal but try from PATH
    import shutil
    if shutil.which('mypy'):
        return ['mypy']
    warning("mypy not found, so can't check config with it. See https://github.com/python/mypy#readme if you want to install it and retry")
    return None


def run_mypy(pkg):
    from .preinit import get_mycfg_dir
    mycfg_dir = get_mycfg_dir()
    # todo ugh. not sure how to extract it from pkg?

    # todo dunno maybe use the same mypy config in repository?
    # I'd need to install mypy.ini then??
    env = {**os.environ}
    mpath = env.get('MYPYPATH')
    mpath = str(mycfg_dir) + ('' if mpath is None else f':{mpath}')
    env['MYPYPATH'] = mpath


    cmd = mypy_cmd()
    if cmd is None:
        return None
    mres = run([
        *cmd,
        '--namespace-packages',
        '--color-output', # not sure if works??
        '--pretty',
        '--show-error-codes',
        '--show-error-context',
        '--check-untyped-defs',
        '-p', pkg.__name__,
    ], stderr=PIPE, stdout=PIPE, env=env)
    return mres


def eprint(x: str):
    print(x, file=sys.stderr)

def indent(x: str) -> str:
    return ''.join('   ' + l for l in x.splitlines(keepends=True))

OK  = '✅'
OFF = '🔲'

def info(x: str):
    eprint(OK + ' ' + x)

def error(x: str):
    eprint('❌ ' + x)

def warning(x: str):
    eprint('❗ ' + x) # todo yellow?

def tb(e):
    tb = ''.join(traceback.format_exception(Exception, e, e.__traceback__))
    sys.stderr.write(indent(tb))


# todo not gonna work on Windows... perhaps make it optional and use colorama/termcolor? (similar to core.warnings)
class color:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


def config_create(args):
    from .preinit import get_mycfg_dir
    mycfg_dir = get_mycfg_dir()

    created = False
    if not mycfg_dir.exists():
        # todo not sure about the layout... should I use my/config.py instead?
        my_config = mycfg_dir / 'my' / 'config' / '__init__.py'

        my_config.parent.mkdir(parents=True)
        my_config.touch()
        info(f'created empty config: {my_config}')
        created = True
    else:
        error(f"config directory '{mycfg_dir}' already exists, skipping creation")

    config_check(args)
    if not created:
        sys.exit(1)


# TODO return the config as a result?
def config_check(args):
    try:
        import my.config as cfg
    except Exception as e:
        error("failed to import the config")
        tb(e)
        sys.exit(1)

    info(f"config file: {cfg.__file__}")

    mres = run_mypy(cfg)
    if mres is None: # no mypy
        return
    rc = mres.returncode
    if rc == 0:
        info('mypy config check: success')
    else:
        error('mypy config check: failed')
        sys.stderr.write(indent(mres.stderr.decode('utf8')))
    sys.stderr.write(indent(mres.stdout.decode('utf8')))


def _modules(all=False):
    from .util import modules
    skipped = []
    for m in modules():
        if not all and m.skip_reason is not None:
            skipped.append(m.name)
        else:
            yield m
    if len(skipped) > 0:
        warning(f'Skipped {len(skipped)} modules: {skipped}. Pass --all if you want to see them.')


def modules_check(args):
    verbose: bool         = args.verbose
    quick:   bool         = args.quick
    module: Optional[str] = args.module
    vw = '' if verbose else '; pass --verbose to print more information'

    from . import common
    common.QUICK_STATS = quick # dirty, but hopefully OK for cli

    tabulate_warnings()

    from .util import get_stats, HPIModule

    mods: Iterable[HPIModule]
    if module is None:
        mods = _modules(all=args.all)
    else:
        mods = [HPIModule(name=module, skip_reason=None)]

    # todo add a --all argument to disregard is_active check?
    for mr in mods:
        skip = mr.skip_reason
        m    = mr.name
        if skip is not None:
            eprint(OFF + f' {color.YELLOW}SKIP{color.RESET}: {m:<50} {skip}')
            continue

        try:
            mod = importlib.import_module(m)
        except Exception as e:
            # todo more specific command?
            error(f'{color.RED}FAIL{color.RESET}: {m:<50} loading failed{vw}')
            if verbose:
                tb(e)
            continue

        info(f'{color.GREEN}OK{color.RESET}  : {m:<50}')
        stats = get_stats(m)
        if stats is None:
            continue

        try:
            res = stats()
        except Exception as ee:
            warning(f'     - {color.RED}stats:{color.RESET}                      computing failed{vw}')
            if verbose:
                tb(ee)
        else:
            info(f'    - stats: {res}')


def list_modules(args) -> None:
    # todo add a --sort argument?
    tabulate_warnings()

    for mr in _modules(all=args.all):
        m    = mr.name
        sr   = mr.skip_reason
        if sr is None:
            pre = OK
            suf = ''
        else:
            pre = OFF
            suf = f' {color.YELLOW}[disabled: {sr}]{color.RESET}'

        print(f'{pre} {m:50}{suf}')


def tabulate_warnings():
    '''
    Helper to avoid visual noise in hpi modules/doctor
    '''
    import warnings
    orig = warnings.formatwarning
    def override(*args, **kwargs):
        res = orig(*args, **kwargs)
        return ''.join('  ' + x for x in res.splitlines(keepends=True))
    warnings.formatwarning = override
    # TODO loggers as well?


# todo check that it finds private modules too?
def doctor(args):
    config_check(args)
    modules_check(args)


def parser():
    from argparse import ArgumentParser
    p = ArgumentParser('Human Programming Interface', epilog='''
Tool for HPI.

Work in progress, will be used for config management, troubleshooting & introspection
''')
    sp = p.add_subparsers(dest='mode')
    dp = sp.add_parser('doctor', help='Run various checks')
    dp.add_argument('--verbose', action='store_true', help='Print more diagnosic infomration')
    dp.add_argument('--all'    , action='store_true', help='List all modules, including disabled')
    dp.add_argument('--quick'  , action='store_true', help='Only run partial checks (first 100 items)')
    dp.add_argument('module', nargs='?', type=str   , help='Pass to check a specific module')
    dp.set_defaults(func=doctor)

    cp = sp.add_parser('config', help='Work with configuration')
    scp = cp.add_subparsers(dest='mode')
    if True:
        ccp = scp.add_parser('check', help='Check config')
        ccp.set_defaults(func=config_check)

        icp = scp.add_parser('create', help='Create user config')
        icp.set_defaults(func=config_create)

    mp = sp.add_parser('modules', help='List available modules')
    mp.add_argument('--all'    , action='store_true', help='List all modules, including disabled')
    mp.set_defaults(func=list_modules)

    return p


def main():
    p = parser()
    args = p.parse_args()

    func = getattr(args, 'func', None)
    if func is None:
        p.print_help()
        sys.exit(1)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # cd into tmp dir to prevent accidental imports..
        os.chdir(str(td))
        func(args)


if __name__ == '__main__':
    main()
