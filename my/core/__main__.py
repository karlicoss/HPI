import functools
import importlib
import os
import sys
import traceback
from typing import Optional, Sequence, Iterable, List
from pathlib import Path
from subprocess import check_call, run, PIPE, CompletedProcess

import click


@functools.lru_cache()
def mypy_cmd() -> Optional[Sequence[str]]:
    try:
        # preferably, use mypy from current python env
        import mypy
        return [sys.executable, '-m', 'mypy']
    except ImportError:
        pass
    # ok, not ideal but try from PATH
    import shutil
    if shutil.which('mypy'):
        return ['mypy']
    warning("mypy not found, so can't check config with it. See https://github.com/python/mypy#readme if you want to install it and retry")
    return None


from types import ModuleType
def run_mypy(pkg: ModuleType) -> Optional[CompletedProcess]:
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


# use click.echo over print since it handles handles possible Unicode errors,
# strips colors if the output is a file
# https://click.palletsprojects.com/en/7.x/quickstart/#echoing
def eprint(x: str) -> None:
    # err=True prints to stderr
    click.echo(x, err=True)

def indent(x: str) -> str:
    return ''.join('   ' + l for l in x.splitlines(keepends=True))

OK  = '✅'
OFF = '🔲'

def info(x: str) -> None:
    eprint(OK + ' ' + x)

def error(x: str) -> None:
    eprint('❌ ' + x)

def warning(x: str) -> None:
    eprint('❗ ' + x) # todo yellow?

def tb(e: Exception) -> None:
    tb = ''.join(traceback.format_exception(Exception, e, e.__traceback__))
    sys.stderr.write(indent(tb))


def config_create() -> None:
    from .preinit import get_mycfg_dir
    mycfg_dir = get_mycfg_dir()

    created = False
    if not mycfg_dir.exists():
        # todo not sure about the layout... should I use my/config.py instead?
        my_config = mycfg_dir / 'my' / 'config' / '__init__.py'

        my_config.parent.mkdir(parents=True)
        my_config.write_text('''
### HPI personal config
## see
# https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-modules
# https://github.com/karlicoss/HPI/blob/master/doc/MODULES.org
## for some help on writing your own config

# to quickly check your config, run:
# hpi config check

# to quickly check a specific module setup, run hpi doctor <module>, e.g.:
# hpi doctor my.reddit

### useful default imports
from my.core import Paths, PathIsh, get_files
###

# most of your configs will look like this:
class example:
    export_path: Paths = '/home/user/data/example_data_dir/'

### you can insert your own configuration below
### but feel free to delete the stuff above if you don't need ti
'''.lstrip())
        info(f'created empty config: {my_config}')
        created = True
    else:
        error(f"config directory '{mycfg_dir}' already exists, skipping creation")

    check_passed = config_ok()
    if not created or not check_passed:
        sys.exit(1)


# TODO return the config as a result?
def config_ok() -> bool:
    errors: List[Exception] = []

    import my
    try:
        paths: List[str] = list(my.__path__) # type: ignore[attr-defined]
    except Exception as e:
        errors.append(e)
        error('failed to determine module import path')
        tb(e)
    else:
        info(f'import order: {paths}')

    try:
        import my.config as cfg
    except Exception as e:
        errors.append(e)
        error("failed to import the config")
        tb(e)
        # todo yield exception here? so it doesn't fail immediately..
        # I guess it's fairly critical and worth exiting immediately
        sys.exit(1)

    cfg_path = cfg.__file__# todo might be better to use __path__?
    info(f"config file : {cfg_path}")

    import my.core as core
    try:
        core_pkg_path = str(Path(core.__path__[0]).parent) # type: ignore[attr-defined]
        if cfg_path.startswith(core_pkg_path):
            error(f'''
Seems that the stub config is used ({cfg_path}). This is likely not going to work.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-modules for more information
'''.strip())
            errors.append(RuntimeError('bad config path'))
    except Exception as e:
        errors.append(e)
        tb(e)

    # todo for some reason compileall.compile_file always returns true??
    try:
        cmd = [sys.executable, '-m', 'compileall', str(cfg_path)]
        check_call(cmd)
        info('syntax check: ' + ' '.join(cmd))
    except Exception as e:
        errors.append(e)

    mres = run_mypy(cfg)
    if mres is not None: # has mypy
        rc = mres.returncode
        if rc == 0:
            info('mypy check  : success')
        else:
            error('mypy check: failed')
            errors.append(RuntimeError('mypy failed'))
            sys.stderr.write(indent(mres.stderr.decode('utf8')))
        sys.stderr.write(indent(mres.stdout.decode('utf8')))

    if len(errors) > 0:
        error(f'config check: {len(errors)} errors')
        return False
    else:
        # note: shouldn't exit here, might run something else
        info('config check: success!')
        return True


from .util import HPIModule, modules
def _modules(*, all: bool=False) -> Iterable[HPIModule]:
    skipped = []
    for m in modules():
        if not all and m.skip_reason is not None:
            skipped.append(m.name)
        else:
            yield m
    if len(skipped) > 0:
        warning(f'Skipped {len(skipped)} modules: {skipped}. Pass --all if you want to see them.')


def modules_check(*, verbose: bool, list_all: bool, quick: bool, for_modules: List[str]) -> None:
    if len(for_modules) > 0:
        # if you're checking specific modules, show errors
        # hopefully makes sense?
        verbose = True
    vw = '' if verbose else '; pass --verbose to print more information'

    from . import common
    common.QUICK_STATS = quick # dirty, but hopefully OK for cli

    tabulate_warnings()

    from .util import get_stats, HPIModule
    from .stats import guess_stats

    mods: Iterable[HPIModule]
    if len(for_modules) == 0:
        mods = _modules(all=list_all)
    else:
        mods = [HPIModule(name=m, skip_reason=None) for m in for_modules]

    # todo add a --all argument to disregard is_active check?
    for mr in mods:
        skip = mr.skip_reason
        m    = mr.name
        if skip is not None:
            eprint(f'{OFF} {click.style("SKIP", fg="yellow")}: {m:<50} {skip}')
            continue

        try:
            mod = importlib.import_module(m)
        except Exception as e:
            # todo more specific command?
            error(f'{click.style("FAIL", fg="red")}: {m:<50} loading failed{vw}')
            if verbose:
                tb(e)
            continue

        info(f'{click.style("OK", fg="green")}  : {m:<50}')
        # first try explicitly defined stats function:
        stats = get_stats(m)
        if stats is None:
            # then try guessing.. not sure if should log somehow?
            stats = guess_stats(m)

        if stats is None:
            eprint("       - no 'stats' function, can't check the data")
            # todo point to a readme on the module structure or something?
            continue

        try:
            res = stats()
            assert res is not None, 'stats() returned None'
        except Exception as ee:
            warning(f'     - {click.style("stats:", fg="red")}                      computing failed{vw}')
            if verbose:
                tb(ee)
        else:
            info(f'    - stats: {res}')


def list_modules(*, list_all: bool) -> None:
    # todo add a --sort argument?
    tabulate_warnings()

    for mr in _modules(all=list_all):
        m    = mr.name
        sr   = mr.skip_reason
        if sr is None:
            pre = OK
            suf = ''
        else:
            pre = OFF
            suf = f' {click.style(f"[disabled: {sr}]", fg="yellow")}'

        click.echo(f'{pre} {m:50}{suf}')


def tabulate_warnings() -> None:
    '''
    Helper to avoid visual noise in hpi modules/doctor
    '''
    import warnings
    orig = warnings.formatwarning
    def override(*args, **kwargs) -> str:
        res = orig(*args, **kwargs)
        return ''.join('  ' + x for x in res.splitlines(keepends=True))
    warnings.formatwarning = override
    # TODO loggers as well?


def _requires(module: str) -> Sequence[str]:
    from .discovery_pure import module_by_name
    mod = module_by_name(module)
    # todo handle when module is missing
    r = mod.requires
    if r is None:
        error(f"Module {module} has no REQUIRES specification")
        sys.exit(1)
    return r


def module_requires(*, module: str) -> None:
    rs = [f"'{x}'" for x in _requires(module)]
    eprint(f'dependencies of {module}')
    for x in rs:
        click.echo(x)


def module_install(*, user: bool, module: str) -> None:
    # TODO hmm. not sure how it's gonna work -- presumably people use different means of installing...
    # how do I install into the 'same' environment??
    import shlex
    cmd = [
        sys.executable, '-m', 'pip', 'install',
        *(['--user'] if user else []), # meh
        *_requires(module),
    ]
    eprint('Running: ' + ' '.join(map(shlex.quote, cmd)))
    check_call(cmd)


@click.group()
def main() -> None:
    '''
    Human Programming Interface

    Tool for HPI
    Work in progress, will be used for config management, troubleshooting & introspection
    '''
    # for potential future reference, if shared state needs to be added to groups
    # https://click.palletsprojects.com/en/7.x/commands/#group-invocation-without-command
    # https://click.palletsprojects.com/en/7.x/commands/#multi-command-chaining

    # acts as a contextmanager of sorts - any subcommand will then run
    # in something like /tmp/hpi_temp_dir
    # to avoid importing relative modules by accident during development
    # maybe can be removed later if theres more test coverage/confidence that nothing
    # would happen?
    import tempfile

    # use a particular directory instead of a random one, since
    # click being decorator based means its more complicated
    # to run things at the end (would need to use a callback or pass context)
    # https://click.palletsprojects.com/en/7.x/commands/#nested-handling-and-contexts

    tdir: str = os.path.join(tempfile.gettempdir(), 'hpi_temp_dir')
    if not os.path.exists(tdir):
        os.makedirs(tdir)
    os.chdir(tdir)


@main.command(name='doctor', short_help='run various checks')
@click.option('--verbose/--quiet', default=False, help='Print more diagnostic information')
@click.option('--all', 'list_all', is_flag=True, help='List all modules, including disabled')
@click.option('--quick', is_flag=True, help='Only run partial checks (first 100 items)')
@click.option('--skip-config-check', 'skip_conf', is_flag=True, help='Skip configuration check')
@click.argument('MODULE', nargs=-1, required=False)
def doctor_cmd(verbose: bool, list_all: bool, quick: bool, skip_conf: bool, module: Sequence[str]) -> None:
    '''
    Run various checks

    MODULE is one or more specific module names to check (e.g. my.reddit)
    Otherwise, checks all modules
    '''
    if not skip_conf:
        config_ok()
    # TODO check that it finds private modules too?
    modules_check(verbose=verbose, list_all=list_all, quick=quick, for_modules=list(module))


@main.group(name='config', short_help='work with configuration')
def config_grp() -> None:
    '''Act on your HPI configuration'''
    pass


@config_grp.command(name='check', short_help='check config')
def config_check_cmd() -> None:
    '''Check your HPI configuration file'''
    ok = config_ok()
    sys.exit(0 if ok else False)


@config_grp.command(name='create', short_help='create user config')
def config_create_cmd() -> None:
    '''Create user configuration file for HPI'''
    config_create()


@main.command(name='modules', short_help='list available modules')
@click.option('--all', 'list_all', is_flag=True, help='List all modules, including disabled')
def module_cmd(list_all: bool) -> None:
    '''List available modules'''
    list_modules(list_all=list_all)


@main.group(name='module', short_help='module management')
def module_grp() -> None:
    '''Module management'''
    pass


@module_grp.command(name='requires', short_help='print module reqs')
@click.argument('MODULE')
def module_requires_cmd(module: str) -> None:
    '''
    Print MODULE requirements

    MODULE is a specific module name (e.g. my.reddit)
    '''
    module_requires(module=module)


@module_grp.command(name='install', short_help='install module deps')
@click.option('--user', is_flag=True, help='same as pip --user')
@click.argument('MODULE')
def module_install_cmd(user: bool, module: str) -> None:
    '''
    Install dependencies for a module using pip

    MODULE is a specific module name (e.g. my.reddit)
    '''
    # todo could add functions to check specific module etc..
    module_install(user=user, module=module)


# todo: add more tests?
# its standard click practice to have the function click calls be a separate
# function from the decorated function, as it allows the application-specific code to be
# more testable. also allows hpi commands to be imported and called manually from
# other python code


def test_requires() -> None:
    from click.testing import CliRunner
    result = CliRunner().invoke(main, ['module', 'requires', 'my.github.ghexport'])
    assert result.exit_code == 0
    assert "github.com/karlicoss/ghexport" in result.output


if __name__ == '__main__':
    # prog_name is so that if this is invoked with python -m my.core
    # this still shows hpi in the help text
    main(prog_name='hpi')
