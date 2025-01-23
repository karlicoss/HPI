from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from my.core.compat import NoneType, assert_never


# TODO Popper? not sure
@dataclass
class Helper:
    manager: 'Manager'
    item: Any  # todo realistically, list or dict? could at least type as indexable or something
    path: tuple[str, ...]

    def pop_if_primitive(self, *keys: str) -> None:
        """
        The idea that primitive TODO
        """
        item = self.item
        for k in keys:
            v = item[k]
            if isinstance(v, (str, bool, float, int, NoneType)):
                item.pop(k)  # todo kinda unfortunate to get dict item twice.. but not sure if can avoid?

    def check(self, key: str, expected: Any) -> None:
        actual = self.item.pop(key)
        assert actual == expected, (key, actual, expected)

    def zoom(self, key: str) -> 'Helper':
        return self.manager.helper(item=self.item.pop(key), path=(*self.path, key))


def is_empty(x) -> bool:
    if isinstance(x, dict):
        return len(x) == 0
    elif isinstance(x, list):
        return all(map(is_empty, x))
    else:
        assert_never(x)  # noqa: RET503


class Manager:
    def __init__(self) -> None:
        self.helpers: list[Helper] = []

    def helper(self, item: Any, *, path: tuple[str, ...] = ()) -> Helper:
        res = Helper(manager=self, item=item, path=path)
        self.helpers.append(res)
        return res

    def check(self) -> Iterator[Exception]:
        remaining = []
        for h in self.helpers:
            # TODO recursively check it's primitive?
            if is_empty(h.item):
                continue
            remaining.append((h.path, h.item))
        if len(remaining) == 0:
            return
        yield RuntimeError(f'Unparsed items remaining: {remaining}')
