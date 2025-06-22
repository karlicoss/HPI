from __future__ import annotations

import functools
import importlib
import inspect
import os
import shlex
import shutil
import sys
import tempfile
import traceback
from collections.abc import Iterable, Sequence
from contextlib import ExitStack
from itertools import chain
from pathlib import Path
from subprocess import PIPE, CompletedProcess, Popen, check_call, run
from typing import Any, Callable

import click


@functools.lru_cache
def mypy_cmd() -> Sequence[str] | None:
    try:
        # preferably, use mypy from current python env
        import mypy  # noqa: F401 fine not to use it
    except ImportError:
        pass
    else:
        return [sys.executable, '-m', 'mypy']
    # ok, not ideal but try from PATH
    if shutil.which('mypy'):
        return ['mypy']
    warning("mypy not found, so can't check config with it. See https://github.com/python/mypy#readme if you want to install it and retry")
    return None


def run_mypy(cfg_path: Path) -> CompletedProcess | None:
    # todo dunno maybe use the same mypy config in repository?
    # I'd need to install mypy.ini then??
    env = {**os.environ}
    mpath = env.get('MYPYPATH')
    mpath = str(cfg_path) + ('' if mpath is None else f':{mpath}')
    env['MYPYPATH'] = mpath

    cmd = mypy_cmd()
    if cmd is None:
        return None
    mres = run([  # noqa: UP022,PLW1510
        *cmd,
        '--namespace-packages',
        '--color-output', # not sure if works??
        '--pretty',
        '--show-error-codes',
        '--show-error-context',
        '--check-untyped-defs',
        '-p', 'my.config',
    ], stderr=PIPE, stdout=PIPE, env=env)
    return mres


# use click.echo over print since it handles handles possible Unicode errors,
# strips colors if the output is a file
# https://click.palletsprojects.com/en/7.x/quickstart/#echoing
def eprint(x: str) -> None:
    # err=True prints to stderr
    click.echo(x, err=True)


def indent(x: str) -> str:
    # todo use textwrap.indent?
    return ''.join('   ' + l for l in x.splitlines(keepends=True))


OK = '✅'
OFF = '🔲'


def info(x: str) -> None:
    eprint(OK + ' ' + x)


def error(x: str) -> None:
    eprint('❌ ' + x)


def warning(x: str) -> None:
    eprint('❗ ' + x)  # todo yellow?


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
        my_config.write_text(
            '''
### HPI personal config
## see
# https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-modules
# https://github.com/karlicoss/HPI/blob/master/doc/MODULES.org
## for some help on writing your own config

# to quickly check your config, run:
# hpi config check

# to quickly check a specific module setup, run hpi doctor <module>, e.g.:
# hpi doctor my.reddit.rexport

### useful default imports
from my.core import Paths, PathIsh, get_files
###

# most of your configs will look like this:
class example:
    export_path: Paths = '/home/user/data/example_data_dir/'

### you can insert your own configuration below
### but feel free to delete the stuff above if you don't need ti
'''.lstrip()
        )
        info(f'created empty config: {my_config}')
        created = True
    else:
        error(f"config directory '{mycfg_dir}' already exists, skipping creation")

    check_passed = config_ok()
    if not created or not check_passed:
        sys.exit(1)


# todo return the config as a result?
def config_ok() -> bool:
    errors: list[Exception] = []

    # at this point 'my' should already be imported, so doesn't hurt to extract paths from it
    import my

    try:
        paths: list[str] = list(my.__path__)
    except Exception as e:
        errors.append(e)
        error('failed to determine module import path')
        tb(e)
    else:
        info(f'import order: {paths}')

    # first try doing as much as possible without actually importing my.config
    from .preinit import get_mycfg_dir

    cfg_path = get_mycfg_dir()
    # alternative is importing my.config and then getting cfg_path from its __file__/__path__
    # not sure which is better tbh

    ## check we're not using stub config
    import my.core

    try:
        core_pkg_path = str(Path(my.core.__path__[0]).parent)
        if str(cfg_path).startswith(core_pkg_path):
            error(
                f'''
Seems that the stub config is used ({cfg_path}). This is likely not going to work.
See https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#setting-up-modules for more information
'''.strip()
            )
            errors.append(RuntimeError('bad config path'))
    except Exception as e:
        errors.append(e)
        tb(e)
    else:
        info(f"config path : {cfg_path}")
    ##

    ## check syntax
    with tempfile.TemporaryDirectory() as td:
        # use a temporary directory, useful because
        # - compileall ignores -B, so always craps with .pyc files (annoyng on RO filesystems)
        # - compileall isn't following symlinks, just silently ignores them
        tdir = Path(td) / 'cfg'
        # NOTE: compileall still returns code 0 if the path doesn't exist..
        # but in our case hopefully it's not an issue
        cmd = [sys.executable, '-m', 'compileall', '-q', str(tdir)]

        try:
            # this will resolve symlinks when copying
            # should be under try/catch since might fail if some symlinks are missing
            shutil.copytree(cfg_path, tdir, dirs_exist_ok=True)
            check_call(cmd)
            info('syntax check: ' + ' '.join(cmd))
        except Exception as e:
            errors.append(e)
            tb(e)
    ##

    ## check types
    mypy_res = run_mypy(cfg_path)
    if mypy_res is not None:  # has mypy
        rc = mypy_res.returncode
        if rc == 0:
            info('mypy check  : success')
        else:
            error('mypy check: failed')
            errors.append(RuntimeError('mypy failed'))
            sys.stderr.write(indent(mypy_res.stderr.decode('utf8')))
        sys.stderr.write(indent(mypy_res.stdout.decode('utf8')))
    ##

    ## finally, try actually importing the config (it should use same cfg_path)
    try:
        import my.config
    except Exception as e:
        errors.append(e)
        error("failed to import the config")
        tb(e)
    ##

    if len(errors) > 0:
        error(f'config check: {len(errors)} errors')
        return False

    # note: shouldn't exit here, might run something else
    info('config check: success!')
    return True


from .util import HPIModule, modules


def _modules(*, all: bool = False) -> Iterable[HPIModule]:  # noqa: A002
    skipped = []
    for m in modules():
        if not all and m.skip_reason is not None:
            skipped.append(m.name)
        else:
            yield m
    if len(skipped) > 0:
        warning(f'Skipped {len(skipped)} modules: {skipped}. Pass --all if you want to see them.')


def modules_check(*, verbose: bool, list_all: bool, quick: bool, for_modules: list[str]) -> None:
    if len(for_modules) > 0:
        # if you're checking specific modules, show errors
        # hopefully makes sense?
        verbose = True
    vw = '' if verbose else '; pass --verbose to print more information'

    tabulate_warnings()

    import contextlib

    from .error import warn_my_config_import_error
    from .stats import get_stats, quick_stats
    from .util import HPIModule

    mods: Iterable[HPIModule]
    if len(for_modules) == 0:
        mods = _modules(all=list_all)
    else:
        mods = [HPIModule(name=m, skip_reason=None) for m in for_modules]

    # todo add a --all argument to disregard is_active check?
    for mr in mods:
        skip = mr.skip_reason
        m = mr.name
        if skip is not None:
            eprint(f'{OFF} {click.style("SKIP", fg="yellow")}: {m:<50} {skip}')
            continue

        try:
            mod = importlib.import_module(m)  # noqa: F841
        except Exception as e:
            # todo more specific command?
            error(f'{click.style("FAIL", fg="red")}: {m:<50} loading failed{vw}')
            # check that this is an import error in particular, not because
            # of a ModuleNotFoundError because some dependency wasn't installed
            if isinstance(e, (ImportError, AttributeError)):
                warn_my_config_import_error(e)
            if verbose:
                tb(e)
            continue

        info(f'{click.style("OK", fg="green")}  : {m:<50}')
        # TODO add hpi 'stats'? instead of doctor? not sure
        stats = get_stats(m, guess=True)

        if stats is None:
            eprint("       - no 'stats' function, can't check the data")
            # todo point to a readme on the module structure or something?
            continue

        quick_context = quick_stats() if quick else contextlib.nullcontext()

        try:
            kwargs = {}
            if 'quick' in inspect.signature(stats).parameters:
                kwargs['quick'] = quick
            with quick_context:
                res = stats(**kwargs)
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
        m = mr.name
        sr = mr.skip_reason
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


def _requires(modules: Sequence[str]) -> Sequence[str]:
    from .discovery_pure import module_by_name

    mods = [module_by_name(module) for module in modules]
    res = []
    for mod in mods:
        if mod.legacy is not None:
            warning(mod.legacy)

        reqs = mod.requires
        if reqs is None:
            warning(f"Module {mod.name} has no REQUIRES specification")
            continue
        for r in reqs:
            if r not in res:
                res.append(r)
    return res


def module_requires(*, module: Sequence[str]) -> None:
    if isinstance(module, str):
        # legacy behavior, used to take a since argument
        module = [module]
    rs = [f"'{x}'" for x in _requires(modules=module)]
    eprint(f'dependencies of {module}')
    for x in rs:
        click.echo(x)


def module_install(*, user: bool, module: Sequence[str], parallel: bool = False, break_system_packages: bool = False) -> None:
    if isinstance(module, str):
        # legacy behavior, used to take a since argument
        module = [module]

    requirements = _requires(module)

    if len(requirements) == 0:
        warning('requirements list is empty, no need to install anything')
        return

    use_uv = 'HPI_MODULE_INSTALL_USE_UV' in os.environ
    pre_cmd = [
        sys.executable, '-m', *(['uv'] if use_uv else []), 'pip',
        'install',
        *(['--user'] if user else []), # todo maybe instead, forward all the remaining args to pip?
        *(['--break-system-packages'] if break_system_packages else []), # https://peps.python.org/pep-0668/
    ]

    cmds = []
    # disable parallel on windows, sometimes throws a
    # '[WinError 32] The process cannot access the file because it is being used by another process'
    # same on mac it seems? possible race conditions which are hard to debug?
    # WARNING: Error parsing requirements for sqlalchemy: [Errno 2] No such file or directory: '/Users/runner/work/HPI/HPI/.tox/mypy-misc/lib/python3.7/site-packages/SQLAlchemy-2.0.4.dist-info/METADATA'
    if parallel and sys.platform not in ['win32', 'cygwin', 'darwin']:
        # todo not really sure if it's safe to install in parallel like this
        # but definitely doesn't hurt to experiment for e.g. mypy pipelines
        # pip has '--use-feature=fast-deps', but it doesn't really work
        # I think it only helps for pypi artifacts (not git!),
        # and only if they weren't cached
        for r in requirements:
            cmds.append([*pre_cmd, r])
    else:
        if parallel:
            warning('parallel install is not supported on this platform, installing sequentially...')
        # install everything in one cmd
        cmds.append(pre_cmd + list(requirements))

    with ExitStack() as exit_stack:
        popens = []
        for cmd in cmds:
            eprint('Running: ' + ' '.join(map(shlex.quote, cmd)))
            popen = exit_stack.enter_context(Popen(cmd))
            popens.append(popen)

        for popen in popens:
            ret = popen.wait()
            assert ret == 0, popen


def _ui_getchar_pick(choices: Sequence[str], prompt: str = 'Select from: ') -> int:
    '''
    Basic menu allowing the user to select one of the choices
    returns the index the user chose
    '''
    assert len(choices) > 0, 'Didnt receive any choices to prompt!'
    eprint(prompt + '\n')

    # prompts like 1,2,3,4,5,6,7,8,9,a,b,c,d,e,f...
    chr_offset = ord('a') - 10

    # dict from key user can press -> resulting index
    result_map = {}
    for i, opt in enumerate(choices, 1):
        char: str = str(i) if i < 10 else chr(i + chr_offset)
        result_map[char] = i - 1
        eprint(f'\t{char}. {opt}')

    eprint('')
    while True:
        ch = click.getchar()
        if ch not in result_map:
            eprint(f'{ch} not in {list(result_map.keys())}')
            continue
        return result_map[ch]


def _locate_functions_or_prompt(qualified_names: list[str], *, prompt: bool = True) -> Iterable[Callable[..., Any]]:
    from .query import QueryException, locate_qualified_function
    from .stats import is_data_provider

    # if not connected to a terminal, can't prompt
    if not sys.stdout.isatty():
        prompt = False

    for qualname in qualified_names:
        try:
            # common-case
            yield locate_qualified_function(qualname)
        except QueryException as qr_err:
            # maybe the user specified a module name instead of a function name?
            # try importing the name the user specified as a module and prompt the
            # user to select a 'data provider' like function
            try:
                mod = importlib.import_module(qualname)
            except Exception as ie:
                eprint(f"During fallback, importing '{qualname}' as module failed")
                raise qr_err from ie

            # find data providers in this module
            data_providers = [f for _, f in inspect.getmembers(mod, inspect.isfunction) if is_data_provider(f)]
            if len(data_providers) == 0:
                eprint(f"During fallback, could not find any data providers in '{qualname}'")
                raise qr_err
            else:
                # was only one data provider-like function, use that
                if len(data_providers) == 1:
                    yield data_providers[0]
                else:
                    choices = [f.__name__ for f in data_providers]
                    if prompt is False:
                        # there's more than one possible data provider in this module,
                        # STDOUT is not a TTY, can't prompt
                        eprint("During fallback, more than one possible data provider, can't prompt since STDOUT is not a TTY")
                        eprint("Specify one of:")
                        for funcname in choices:
                            eprint(f"\t{qualname}.{funcname}")
                        raise qr_err
                    # prompt the user to pick the function to use
                    chosen_index = _ui_getchar_pick(choices, f"Which function should be used from '{qualname}'?")
                    # respond to the user, so they know something has been picked
                    eprint(f"Selected '{choices[chosen_index]}'")
                    yield data_providers[chosen_index]


def _warn_exceptions(exc: Exception) -> None:
    from my.core import make_logger

    logger = make_logger('CLI', level='warning')

    logger.exception(f'hpi query: {exc}')


# handle the 'hpi query' call
# can raise a QueryException, caught in the click command
def query_hpi_functions(
    *,
    output: str = 'json',
    stream: bool = False,
    qualified_names: list[str],
    order_key: str | None,
    order_by_value_type: type | None,
    after: Any,
    before: Any,
    within: Any,
    reverse: bool = False,
    limit: int | None,
    drop_unsorted: bool,
    wrap_unsorted: bool,
    warn_exceptions: bool,
    raise_exceptions: bool,
    drop_exceptions: bool,
) -> None:
    from .query_range import RangeTuple, select_range

    # chain list of functions from user, in the order they wrote them on the CLI
    input_src = chain(*(f() for f in _locate_functions_or_prompt(qualified_names)))

    # NOTE: if passing just one function to this which returns a single namedtuple/dataclass,
    # using both --order-key and --order-type will often be faster as it does not need to
    # duplicate the iterator in memory, or try to find the --order-type type on each object before sorting
    res = select_range(
        input_src,
        order_key=order_key,
        order_by_value_type=order_by_value_type,
        unparsed_range=RangeTuple(after=after, before=before, within=within),
        reverse=reverse,
        limit=limit,
        drop_unsorted=drop_unsorted,
        wrap_unsorted=wrap_unsorted,
        warn_exceptions=warn_exceptions,
        warn_func=_warn_exceptions,
        raise_exceptions=raise_exceptions,
        drop_exceptions=drop_exceptions,
    )

    if output == 'json':
        from .serialize import dumps

        if stream:
            for item in res:
                # use sys.stdout directly
                # the overhead form click.echo isn't a *lot*, but when called in a loop
                # with potentially millions of items it makes a noticeable difference
                sys.stdout.write(dumps(item))
                sys.stdout.write('\n')
            sys.stdout.flush()
        else:
            click.echo(dumps(list(res)))
    elif output == 'pprint':
        from pprint import pprint

        if stream:
            for item in res:
                pprint(item)
        else:
            pprint(list(res))
    elif output == 'gpx':
        from my.location.common import locations_to_gpx

        # if user didn't specify to ignore exceptions, warn if locations_to_gpx
        # cannot process the output of the command. This can be silenced by
        # passing --drop-exceptions
        if not raise_exceptions and not drop_exceptions:
            warn_exceptions = True

        # can ignore the mypy warning here, locations_to_gpx yields any errors
        # if you didnt pass it something that matches the LocationProtocol
        for exc in locations_to_gpx(res, sys.stdout):  # type: ignore[arg-type]
            if warn_exceptions:
                _warn_exceptions(exc)
            elif raise_exceptions:
                raise exc
            elif drop_exceptions:
                pass
        sys.stdout.flush()
    else:
        res = list(res)  # type: ignore[assignment]
        # output == 'repl'
        eprint(f"\nInteract with the results by using the {click.style('res', fg='green')} variable\n")
        try:
            import IPython  # type: ignore[import,unused-ignore]
        except ModuleNotFoundError:
            eprint("'repl' typically uses ipython, install it with 'python3 -m pip install ipython'. falling back to stdlib...")
            import code

            code.interact(local=locals())
        else:
            IPython.embed()


@click.group()
@click.option("--debug", is_flag=True, default=False, help="Show debug logs")
def main(*, debug: bool) -> None:
    '''
    Human Programming Interface

    Tool for HPI
    Work in progress, will be used for config management, troubleshooting & introspection
    '''
    # should overwrite anything else in LOGGING_LEVEL_HPI
    if debug:
        os.environ['LOGGING_LEVEL_HPI'] = 'debug'

    # for potential future reference, if shared state needs to be added to groups
    # https://click.palletsprojects.com/en/7.x/commands/#group-invocation-without-command
    # https://click.palletsprojects.com/en/7.x/commands/#multi-command-chaining

    # acts as a contextmanager of sorts - any subcommand will then run
    # in something like /tmp/hpi_temp_dir
    # to avoid importing relative modules by accident during development
    # maybe can be removed later if there's more test coverage/confidence that nothing
    # would happen?

    # use a particular directory instead of a random one, since
    # click being decorator based means its more complicated
    # to run things at the end (would need to use a callback or pass context)
    # https://click.palletsprojects.com/en/7.x/commands/#nested-handling-and-contexts

    tdir = Path(tempfile.gettempdir()) / 'hpi_temp_dir'
    tdir.mkdir(exist_ok=True)
    os.chdir(tdir)


@functools.lru_cache(maxsize=1)
def _all_mod_names() -> list[str]:
    """Should include all modules, in case user is trying to diagnose issues"""
    # sort this, so that the order doesn't change while tabbing through
    return sorted([m.name for m in modules()])


def _module_autocomplete(ctx: click.Context, args: Sequence[str], incomplete: str) -> list[str]:
    return [m for m in _all_mod_names() if m.startswith(incomplete)]


@main.command(name='doctor', short_help='run various checks')
@click.option('--verbose/--quiet', default=False, help='Print more diagnostic information')
@click.option('--all', 'list_all', is_flag=True, help='List all modules, including disabled')
@click.option('-q', '--quick', is_flag=True, help='Only run partial checks (first 100 items)')
@click.option('-S', '--skip-config-check', 'skip_conf', is_flag=True, help='Skip configuration check')
@click.argument('MODULE', nargs=-1, required=False, shell_complete=_module_autocomplete)
def doctor_cmd(*, verbose: bool, list_all: bool, quick: bool, skip_conf: bool, module: Sequence[str]) -> None:
    '''
    Run various checks

    MODULE is one or more specific module names to check (e.g. my.reddit.rexport)
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
def module_cmd(*, list_all: bool) -> None:
    '''List available modules'''
    list_modules(list_all=list_all)


@main.group(name='module', short_help='module management')
def module_grp() -> None:
    '''Module management'''
    pass


@module_grp.command(name='requires', short_help='print module reqs')
@click.argument('MODULES', shell_complete=_module_autocomplete, nargs=-1, required=True)
def module_requires_cmd(*, modules: Sequence[str]) -> None:
    '''
    Print MODULES requirements

    MODULES is one or more specific module names (e.g. my.reddit.rexport)
    '''
    module_requires(module=modules)


@module_grp.command(name='install', short_help='install module deps')
@click.option('--user', is_flag=True, help='same as pip --user')
@click.option('--parallel', is_flag=True, help='EXPERIMENTAL. Install dependencies in parallel.')
@click.option('-B',
              '--break-system-packages',
              is_flag=True,
              help='Bypass PEP 668 and install dependencies into the system-wide python package directory.')
@click.argument('MODULES', shell_complete=_module_autocomplete, nargs=-1, required=True)
def module_install_cmd(*, user: bool, parallel: bool, break_system_packages: bool, modules: Sequence[str]) -> None:
    '''
    Install dependencies for modules using pip

    MODULES is one or more specific module names (e.g. my.reddit.rexport)
    '''
    # todo could add functions to check specific module etc..
    module_install(user=user, module=modules, parallel=parallel, break_system_packages=break_system_packages)


@main.command(name='query', short_help='query the results of a HPI function')
@click.option('-o',
              '--output',
              default='json',
              type=click.Choice(['json', 'pprint', 'repl', 'gpx']),
              help='what to do with the result [default: json]')
@click.option('-s',
              '--stream',
              default=False,
              is_flag=True,
              help='stream objects from the data source instead of printing a list at the end')
@click.option('-k',
              '--order-key',
              default=None,
              type=str,
              help='order by an object attribute or dict key on the individual objects returned by the HPI function')
@click.option('-t',
              '--order-type',
              default=None,
              type=click.Choice(['datetime', 'date', 'int', 'float']),
              help='order by searching for some type on the iterable')
@click.option('-a',
              '--after',
              default=None,
              type=str,
              help='while ordering, filter items for the key or type larger than or equal to this')
@click.option('-b',
              '--before',
              default=None,
              type=str,
              help='while ordering, filter items for the key or type smaller than this')
@click.option('-w',
              '--within',
              default=None,
              type=str,
              help="a range 'after' or 'before' to filter items by. see above for further explanation")
@click.option('-r',
              '--recent',
              default=None,
              type=str,
              help="a shorthand for '--order-type datetime --reverse --before now --within'. e.g. --recent 5d")
@click.option('--reverse/--no-reverse',
              default=False,
              help='reverse the results returned from the functions')
@click.option('-l',
              '--limit',
              default=None,
              type=int,
              help='limit the number of items returned from the (functions)')
@click.option('--drop-unsorted',
              default=False,
              is_flag=True,
              help="if the order of an item can't be determined while ordering, drop those items from the results")
@click.option('--wrap-unsorted',
              default=False,
              is_flag=True,
              help="if the order of an item can't be determined while ordering, wrap them into an 'Unsortable' object")
@click.option('--warn-exceptions',
              default=False,
              is_flag=True,
              help="if any errors are returned, print them as errors on STDERR")
@click.option('--raise-exceptions',
              default=False,
              is_flag=True,
              help="if any errors are returned (as objects, not raised) from the functions, raise them")
@click.option('--drop-exceptions',
              default=False,
              is_flag=True,
              help='ignore any errors returned as objects from the functions')
@click.argument('FUNCTION_NAME', nargs=-1, required=True, shell_complete=_module_autocomplete)
def query_cmd(
    *,
    function_name: Sequence[str],
    output: str,
    stream: bool,
    order_key: str | None,
    order_type: str | None,
    after: str | None,
    before: str | None,
    within: str | None,
    recent: str | None,
    reverse: bool,
    limit: int | None,
    drop_unsorted: bool,
    wrap_unsorted: bool,
    warn_exceptions: bool,
    raise_exceptions: bool,
    drop_exceptions: bool,
) -> None:
    '''
    This allows you to query the results from one or more functions in HPI

    By default this runs with '-o json', converting the results
    to JSON and printing them to STDOUT

    You can specify '-o pprint' to just print the objects using their
    repr, or '-o repl' to drop into a ipython shell with access to the results

    While filtering using --order-key datetime, the --after, --before and --within
    flags parse the input to their datetime and timedelta equivalents. datetimes can
    be epoch time, the string 'now', or an date formatted in the ISO format. timedelta
    (durations) are parsed from a similar format to the GNU 'sleep' command, e.g.
    1w2d8h5m20s -> 1 week, 2 days, 8 hours, 5 minutes, 20 seconds

    As an example, to query reddit comments I've made in the last month

    \b
    hpi query --order-type datetime --before now --within 4w my.reddit.all.comments
    or...
    hpi query --recent 4w my.reddit.all.comments

    \b
    Can also query within a range. To filter comments between 2016 and 2018:
    hpi query --order-type datetime --after '2016-01-01' --before '2019-01-01' my.reddit.all.comments
    '''

    from datetime import date, datetime

    chosen_order_type: type | None
    if order_type == "datetime":
        chosen_order_type = datetime
    elif order_type == "date":
        chosen_order_type = date
    elif order_type == "int":
        chosen_order_type = int
    elif order_type == "float":
        chosen_order_type = float
    else:
        chosen_order_type = None

    if recent is not None:
        before = "now"
        chosen_order_type = chosen_order_type or datetime  # dont override if the user specified date
        within = recent
        reverse = not reverse

    from .query import QueryException

    try:
        query_hpi_functions(
            output=output,
            stream=stream,
            qualified_names=list(function_name),
            order_key=order_key,
            order_by_value_type=chosen_order_type,
            after=after,
            before=before,
            within=within,
            reverse=reverse,
            limit=limit,
            drop_unsorted=drop_unsorted,
            wrap_unsorted=wrap_unsorted,
            warn_exceptions=warn_exceptions,
            raise_exceptions=raise_exceptions,
            drop_exceptions=drop_exceptions,
        )
    except QueryException as qe:
        eprint(str(qe))
        sys.exit(1)


# todo: add more tests?
# its standard click practice to have the function click calls be a separate
# function from the decorated function, as it allows the application-specific code to be
# more testable. also allows hpi commands to be imported and called manually from
# other python code


def test_requires() -> None:
    from click.testing import CliRunner

    result = CliRunner().invoke(main, ['module', 'requires', 'my.github.ghexport', 'my.browser.export'])
    assert result.exit_code == 0
    assert "github.com/karlicoss/ghexport" in result.output
    assert "browserexport" in result.output


if __name__ == '__main__':
    # prog_name is so that if this is invoked with python -m my.core
    # this still shows hpi in the help text
    main(prog_name='hpi')
