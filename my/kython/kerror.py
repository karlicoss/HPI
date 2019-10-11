from typing import Union, TypeVar, Iterator, Callable, Iterable, List, Tuple, Type


T = TypeVar('T')
E = TypeVar('E', bound=Exception)

ResT = Union[T, E]

Res = ResT[T, Exception]


# TODO make it a bit more typed??
def is_error(res: Res[T]) -> bool:
    return isinstance(res, Exception)


def is_ok(res: Res[T]) -> bool:
    return not is_error(res)


def unwrap(res: Res[T]) -> T:
    if isinstance(res, Exception):
        raise res
    else:
        return res


def split_errors(l: Iterable[ResT[T, E]], ET=Exception) -> Tuple[List[T], List[E]]:
    rl: List[T] = []
    el: List[E] = []
    for x in l:
        if isinstance(x, ET):
            el.append(x)
        else:
            rl.append(x) # type: ignore
    return rl, el


def ytry(cb) -> Iterator[Exception]:
    try:
        cb()
    except Exception as e:
        yield e


# TODO experimental, not sure if I like it
def echain(ex: E, cause: Exception) -> E:
    ex.__cause__ = cause
    # TODO assert cause is none?
    # TODO copy??
    return ex
    # try:
    #     # TODO is there a awy to get around raise from?
    #     raise ex from cause
    # except Exception as e:
    #     if isinstance(e, type(ex)):
    #         return e
    #     else:
    #         raise e


def sort_res_by(items: Iterable[ResT], key) -> List[ResT]:
    """
    The general idea is: just alaways carry errors with the entry that precedes them
    """
    # TODO ResT object should hold exception class?...
    group = []
    groups = []
    for i in items:
        if isinstance(i, Exception):
            group.append(i)
        else:
            groups.append((i, group))
            group = []

    results = []
    for v, errs in sorted(groups, key=lambda p: key(p[0])):
        results.extend(errs)
        results.append(v)
    results.extend(group)

    return results


def test_sort_res_by():
    class Exc(Exception):
        def __eq__(self, other):
            return self.args == other.args

    ress = [
        Exc('first'),
        Exc('second'),
        5,
        3,
        Exc('xxx'),
        2,
        1,
        Exc('last'),
    ]
    results = sort_res_by(ress, lambda x: x) # type: ignore
    assert results == [
        1,
        Exc('xxx'),
        2,
        3,
        Exc('first'),
        Exc('second'),
        5,
        Exc('last'),
    ]

    results2 = sort_res_by(ress + [0], lambda x: x) # type: ignore
    assert results2 == [Exc('last'), 0] + results[:-1]

