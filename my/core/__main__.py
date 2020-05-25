import os
from pathlib import Path
import sys
from subprocess import check_call, run, PIPE
import traceback

from . import LazyLogger

log = LazyLogger('HPI cli')

class Modes:
    HELLO  = 'hello'
    CONFIG = 'config'
    DOCTOR = 'doctor'


def run_mypy(pkg):
    from .init import get_mycfg_dir
    mycfg_dir = get_mycfg_dir()
    # todo ugh. not sure how to extract it from pkg?

    # todo dunno maybe use the same mypy config in repository?
    # I'd need to install mypy.ini then??
    env = {**os.environ}
    mpath = env.get('MYPYPATH')
    mpath = str(mycfg_dir) + ('' if mpath is None else f':{mpath}')
    env['MYPYPATH'] = mpath

    mres = run([
        'python3', '-m', 'mypy',
        '--namespace-packages',
        '--color-output', # not sure if works??
        '--pretty',
        '--show-error-codes',
        '--show-error-context',
        '--check-untyped-defs',
        '-p', pkg.__name__,
    ], stderr=PIPE, stdout=PIPE, env=env)
    return mres


def config_check(args):
    def eprint(x: str):
        print(x, file=sys.stderr)

    def indent(x: str) -> str:
        return ''.join('   ' + l for l in x.splitlines(keepends=True))

    def info(x: str):
        eprint('✅ ' + x)

    def error(x: str):
        eprint('❌ ' + x)

    def warning(x: str):
        eprint('❗ ' + x) # todo yellow?

    try:
        import my.config as cfg
    except Exception as e:
        error("failed to import the config")
        tb = ''.join(traceback.format_exception(Exception, e, e.__traceback__))
        sys.stderr.write(indent(tb))
        sys.exit(1)

    info(f"config file: {cfg.__file__}")

    try:
        import mypy
    except ImportError:
        warning("mypy not found, can't check config with it")
    else:
        mres = run_mypy(cfg)
        rc = mres.returncode
        if rc == 0:
            info('mypy check: success')
        else:
            error('mypy check: failed')
            sys.stderr.write(indent(mres.stderr.decode('utf8')))
        sys.stderr.write(indent(mres.stdout.decode('utf8')))


def doctor(args):
    config_check(args)


def hello(args):
    print('Hello')


def parser():
    from argparse import ArgumentParser
    p = ArgumentParser('Human Programming Interface', epilog='''
Tool for HPI.

Work in progress, will be used for config management, troubleshooting & introspection
''')
    sp = p.add_subparsers(dest='mode')
    hp = sp.add_parser(Modes.HELLO , help='TODO just a stub, remove later')
    hp.set_defaults(func=hello)

    dp = sp.add_parser(Modes.DOCTOR, help='Run various checks')
    dp.set_defaults(func=doctor)

    cp = sp.add_parser(Modes.CONFIG, help='Work with configuration')
    scp = cp.add_subparsers(dest='mode')
    # if True:
    #     ccp = scp.add_parser('check', help='Check config')
    #     ccp.set_defaults(func=config_check)

    return p


def main():
    p = parser()
    args = p.parse_args()

    func = args.func
    if func is None:
        # shouldn't happen.. but just in case
        p.print_usage()
        sys.exit(1)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # cd into tmp dir to prevent accidental imports..
        os.chdir(str(td))
        args.func(args)


if __name__ == '__main__':
    main()
