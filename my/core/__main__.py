import functools
import importlib
import inspect
import os
import sys
import traceback
from typing import Optional, Sequence, Iterable, List, Type, Any, Callable
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
# hpi doctor my.reddit.rexport

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

    tabulate_warnings()

    import contextlib

    from .common import quick_stats
    from .util import get_stats, HPIModule
    from .stats import guess_stats
    from .error import warn_my_config_import_error

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
            # check that this is an import error in particular, not because
            # of a ModuleNotFoundError because some dependency wasnt installed
            if isinstance(e, (ImportError, AttributeError)):
                warn_my_config_import_error(e)
            if verbose:
                tb(e)
            continue

        info(f'{click.style("OK", fg="green")}  : {m:<50}')
        # first try explicitly defined stats function:
        stats = get_stats(m)
        if stats is None:
            # then try guessing.. not sure if should log somehow?
            stats = guess_stats(m, quick=quick)

        if stats is None:
            eprint("       - no 'stats' function, can't check the data")
            # todo point to a readme on the module structure or something?
            continue

        quick_context = quick_stats() if quick else contextlib.nullcontext()

        try:
            kwargs = {}
            if callable(stats) and 'quick' in inspect.signature(stats).parameters:
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


def _locate_functions_or_prompt(qualified_names: List[str], prompt: bool = True) -> Iterable[Callable[..., Any]]:
    from .query import locate_qualified_function, QueryException
    from .stats import is_data_provider

    # if not connected to a terminal, cant prompt
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
            except Exception:
                eprint(f"During fallback, importing '{qualname}' as module failed")
                raise qr_err

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
                        # theres more than one possible data provider in this module,
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


# handle the 'hpi query' call
# can raise a QueryException, caught in the click command
def query_hpi_functions(
    *,
    output: str = 'json',
    stream: bool = False,
    qualified_names: List[str],
    order_key: Optional[str],
    order_by_value_type: Optional[Type],
    after: Any,
    before: Any,
    within: Any,
    reverse: bool = False,
    limit: Optional[int],
    drop_unsorted: bool,
    wrap_unsorted: bool,
    raise_exceptions: bool,
    drop_exceptions: bool,
) -> None:

    from itertools import chain

    from .query_range import select_range, RangeTuple

    # chain list of functions from user, in the order they wrote them on the CLI
    input_src = chain(*(f() for f in _locate_functions_or_prompt(qualified_names)))

    res = select_range(
        input_src,
        order_key=order_key,
        order_by_value_type=order_by_value_type,
        unparsed_range=RangeTuple(after=after, before=before, within=within),
        reverse=reverse,
        limit=limit,
        drop_unsorted=drop_unsorted,
        wrap_unsorted=wrap_unsorted,
        raise_exceptions=raise_exceptions,
        drop_exceptions=drop_exceptions)

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
    else:
        res = list(res)  # type: ignore[assignment]
        # output == 'repl'
        eprint(f"\nInteract with the results by using the {click.style('res', fg='green')} variable\n")
        try:
            import IPython  # type: ignore[import]
        except ModuleNotFoundError:
            eprint("'repl' typically uses ipython, install it with 'python3 -m pip install ipython'. falling back to stdlib...")
            import code
            code.interact(local=locals())
        else:
            IPython.embed()


@click.group()
@click.option("--debug", is_flag=True, default=False, help="Show debug logs")
def main(debug: bool) -> None:
    '''
    Human Programming Interface

    Tool for HPI
    Work in progress, will be used for config management, troubleshooting & introspection
    '''
    # should overwrite anything else in HPI_LOGS
    if debug:
        os.environ["HPI_LOGS"] = "debug"

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


@functools.lru_cache(maxsize=1)
def _all_mod_names() -> List[str]:
    """Should include all modules, in case user is trying to diagnose issues"""
    # sort this, so that the order doesn't change while tabbing through
    return sorted([m.name for m in modules()])


def _module_autocomplete(ctx: click.Context, args: Sequence[str], incomplete: str) -> List[str]:
    return [m for m in _all_mod_names() if m.startswith(incomplete)]


@main.command(name='doctor', short_help='run various checks')
@click.option('--verbose/--quiet', default=False, help='Print more diagnostic information')
@click.option('--all', 'list_all', is_flag=True, help='List all modules, including disabled')
@click.option('-q', '--quick', is_flag=True, help='Only run partial checks (first 100 items)')
@click.option('-S', '--skip-config-check', 'skip_conf', is_flag=True, help='Skip configuration check')
@click.argument('MODULE', nargs=-1, required=False, shell_complete=_module_autocomplete)
def doctor_cmd(verbose: bool, list_all: bool, quick: bool, skip_conf: bool, module: Sequence[str]) -> None:
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
def module_cmd(list_all: bool) -> None:
    '''List available modules'''
    list_modules(list_all=list_all)


@main.group(name='module', short_help='module management')
def module_grp() -> None:
    '''Module management'''
    pass


@module_grp.command(name='requires', short_help='print module reqs')
@click.argument('MODULE', shell_complete=_module_autocomplete)
def module_requires_cmd(module: str) -> None:
    '''
    Print MODULE requirements

    MODULE is a specific module name (e.g. my.reddit.rexport)
    '''
    module_requires(module=module)


@module_grp.command(name='install', short_help='install module deps')
@click.option('--user', is_flag=True, help='same as pip --user')
@click.argument('MODULE', shell_complete=_module_autocomplete)
def module_install_cmd(user: bool, module: str) -> None:
    '''
    Install dependencies for a module using pip

    MODULE is a specific module name (e.g. my.reddit.rexport)
    '''
    # todo could add functions to check specific module etc..
    module_install(user=user, module=module)


@main.command(name='query', short_help='query the results of a HPI function')
@click.option('-o',
              '--output',
              default='json',
              type=click.Choice(['json', 'pprint', 'repl']),
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
    function_name: Sequence[str],
    output: str,
    stream: bool,
    order_key: Optional[str],
    order_type: Optional[str],
    after: Optional[str],
    before: Optional[str],
    within: Optional[str],
    recent: Optional[str],
    reverse: bool,
    limit: Optional[int],
    drop_unsorted: bool,
    wrap_unsorted: bool,
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
    hpi query --order-type datetime --after '2016-01-01 00:00:00' --before '2019-01-01 00:00:00' my.reddit.all.comments
    '''

    from datetime import datetime, date

    chosen_order_type: Optional[Type]
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
            raise_exceptions=raise_exceptions,
            drop_exceptions=drop_exceptions)
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
    result = CliRunner().invoke(main, ['module', 'requires', 'my.github.ghexport'])
    assert result.exit_code == 0
    assert "github.com/karlicoss/ghexport" in result.output


if __name__ == '__main__':
    # prog_name is so that if this is invoked with python -m my.core
    # this still shows hpi in the help text
    main(prog_name='hpi')
