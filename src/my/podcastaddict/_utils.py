# todo move to hpi core? depends if it's useful for other modules
from __future__ import annotations

from typing import Any, Callable


def dict_diff(a: dict, b: dict) -> dict:
    """
    >>> dict_diff({'d': 1, 'a': 5, 'b': 2}, {'d': 2, 'a': 5, 'c': 4})
    {'d': (1, 2), 'b': (2, None), 'c': (None, 4)}
    """
    diff = {}
    for key, av in a.items():
        if key not in b:
            diff[key] = (av, None)
        else:
            bv = b[key]
            if av != bv:
                diff[key] = (av, bv)

    for key, bv in b.items():
        if key not in a:
            diff[key] = (None, bv)
        # otherwise already handled in other loop
    return diff


# todo maybe move to .core.sqlite? not sure
DbRow = dict[str, Any]


_I = dict[str, Any]


class MultiKeyTracker:
    """
    Helper to find equivalence between dicts that don't have a unique key, but multiple attributes that might overlap
    """

    def __init__(
        self,
        *,
        keys: list[tuple[str, Any]],
        updater: Callable[[_I, _I], None],
    ) -> None:
        self.items: list[tuple[Any, _I]] = []
        self.keys = keys
        self.updater = updater

    def _key(self, item: _I) -> set:
        r = {}
        for k, invalid in self.keys:
            kv = item.get(k)
            if kv in {invalid, None}:
                continue
            r[k] = kv
        return set(r.items())

    def set(self, item: _I, *, add: bool, update: bool) -> _I | None:  # FIXME add types
        rk = self._key(item)
        for kk, v in self.items:
            if len(kk & rk) == 0:
                continue
            # found equivalent item
            if update:
                self.updater(v, item)
                kk.update(rk)
            return v  # return previously present row
        if add:
            self.items.append((rk, item))
        return None

    def get(self, item: _I) -> _I:
        res = self.set(item, add=False, update=False)
        assert res is not None
        return res
