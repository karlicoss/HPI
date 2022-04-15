"""
Various error handling helpers
See https://beepb00p.xyz/mypy-error-handling.html#kiss for more detail
"""

from itertools import tee
from typing import Union, TypeVar, Iterable, List, Tuple, Type, Optional, Callable, Any, cast

from .compat import Literal


T = TypeVar('T')
E = TypeVar('E', bound=Exception) # TODO make covariant?

ResT = Union[T, E]

Res = ResT[T, Exception]

ErrorPolicy = Literal["yield", "raise", "drop"]

def notnone(x: Optional[T]) -> T:
    assert x is not None
    return x


def unwrap(res: Res[T]) -> T:
    if isinstance(res, Exception):
        raise res
    else:
        return res


def echain(ex: E, cause: Exception) -> E:
    ex.__cause__ = cause
    return ex


def split_errors(l: Iterable[ResT[T, E]], ET: Type[E]) -> Tuple[Iterable[T], Iterable[E]]:
    # TODO would be nice to have ET=Exception default? but it causes some mypy complaints?
    vit, eit = tee(l)
    # TODO ugh, not sure if I can reconcile type checking and runtime and convince mypy that ET and E are the same type?
    values: Iterable[T] = (
        r # type: ignore[misc]
        for r in vit
        if not isinstance(r, ET))
    errors: Iterable[E] = (
        r
        for r in eit
        if     isinstance(r, ET))
    # TODO would be interesting to be able to have yield statement anywehere in code
    # so there are multiple 'entry points' to the return value
    return (values, errors)


K = TypeVar('K')
def sort_res_by(items: Iterable[Res[T]], key: Callable[[Any], K]) -> List[Res[T]]:
    """
    Sort a sequence potentially interleaved with errors/entries on which the key can't be computed.
    The general idea is: the error sticks to the non-error entry that follows it
    """
    group = []
    groups = []
    for i in items:
        k: Optional[K]
        try:
            k = key(i)
        except Exception as e:
            k = None
        group.append(i)
        if k is not None:
            groups.append((k, group))
            group = []

    results: List[Res[T]] = []
    for v, grp in sorted(groups, key=lambda p: p[0]): # type: ignore[return-value, arg-type] # TODO SupportsLessThan??
        results.extend(grp)
    results.extend(group) # handle last group (it will always be errors only)

    return results


def test_sort_res_by() -> None:
    class Exc(Exception):
        def __eq__(self, other):
            return self.args == other.args

    ress = [
        Exc('first'),
        Exc('second'),
        5,
        3,
        'bad',
        2,
        1,
        Exc('last'),
    ]
    results = sort_res_by(ress, lambda x: int(x)) # type: ignore
    assert results == [
        1,
        'bad',
        2,
        3,
        Exc('first'),
        Exc('second'),
        5,
        Exc('last'),
    ]

    results2 = sort_res_by(ress + [0], lambda x: int(x)) # type: ignore
    assert results2 == [Exc('last'), 0] + results[:-1]

    assert sort_res_by(['caba', 'a', 'aba', 'daba'], key=lambda x: len(x)) == ['a', 'aba', 'caba', 'daba']
    assert sort_res_by([], key=lambda x: x) == [] # type: ignore


# helpers to associate timestamps with the errors (so something meaningful could be displayed on the plots, for example)
# todo document it under 'patterns' somewhere...

# todo proper typevar?
from datetime import datetime
def set_error_datetime(e: Exception, dt: Optional[datetime]) -> None:
    if dt is None:
        return
    e.args = e.args + (dt,)
    # todo not sure if should return new exception?

def attach_dt(e: Exception, *, dt: Optional[datetime]) -> Exception:
    set_error_datetime(e, dt)
    return e

# todo it might be problematic because might mess with timezones (when it's converted to string, it's converted to a shift)
def extract_error_datetime(e: Exception) -> Optional[datetime]:
    import re
    from datetime import datetime
    for x in reversed(e.args):
        if isinstance(x, datetime):
            return x
        if not isinstance(x, str):
            continue
        m = re.search(r'\d{4}-\d\d-\d\d(...:..:..)?(\.\d{6})?(\+.....)?', x)
        if m is None:
            continue
        ss = m.group(0)
        # todo not sure if should be defensive??
        return datetime.fromisoformat(ss)
    return None


import traceback
from .common import Json
def error_to_json(e: Exception) -> Json:
    estr = ''.join(traceback.format_exception(Exception, e, e.__traceback__))
    return {'error': estr}


MODULE_SETUP_URL = 'https://github.com/karlicoss/HPI/blob/master/doc/SETUP.org#private-configuration-myconfig'

def warn_my_config_import_error(err: Union[ImportError, AttributeError], help_url: str = MODULE_SETUP_URL) -> bool:
    """
    If the user tried to import something from my.config but it failed,
    possibly due to missing the config block in my.config?

    Returns True if it matched a possible config error
    """
    import re
    import click
    if type(err) == ImportError:
        if err.name != 'my.config':
            return False
        # parse name that user attempted to import
        em = re.match(r"cannot import name '(\w+)' from 'my.config'", str(err))
        if em is not None:
            section_name = em.group(1)
            click.secho(f"""\
You may be missing the '{section_name}' section from your config.
See {help_url}\
""", fg='yellow', err=True)
            return True
    elif type(err) == AttributeError:
        # test if user had a nested config block missing
        # https://github.com/karlicoss/HPI/issues/223
        if hasattr(err, 'obj') and hasattr(err, "name"):
            config_obj = cast(object, getattr(err, 'obj'))  # the object that caused the attribute error
            # e.g. active_browser for my.browser
            nested_block_name = err.name  # type: ignore[attr-defined]
            if config_obj.__module__ == 'my.config':
                click.secho(f"""You're likely missing the nested config block for '{getattr(config_obj, '__name__', str(config_obj))}.{nested_block_name}'.
See {help_url} or check the corresponding module.py file for an example\
""", fg='yellow', err=True)
                return True
    else:
        click.echo(f"Unexpected error... {err}", err=True)
    return False



def test_datetime_errors() -> None:
    import pytz
    dt_notz = datetime.now()
    dt_tz   = datetime.now(tz=pytz.timezone('Europe/Amsterdam'))
    for dt in [dt_tz, dt_notz]:
        e1 = RuntimeError('whatever')
        assert extract_error_datetime(e1) is None
        set_error_datetime(e1, dt=dt)
        assert extract_error_datetime(e1) == dt

        e2 = RuntimeError(f'something something {dt} something else')
        assert extract_error_datetime(e2) == dt


    e3 = RuntimeError(str(['one', '2019-11-27T08:56:00', 'three']))
    assert extract_error_datetime(e3) is not None

    # date only
    e4 = RuntimeError(str(['one', '2019-11-27', 'three']))
    assert extract_error_datetime(e4) is not None
