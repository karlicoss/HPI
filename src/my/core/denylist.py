"""
A helper module for defining denylists for sources programmatically
(in lamens terms, this lets you remove some output from a module you don't want)

For docs, see doc/DENYLIST.md
"""

from __future__ import annotations

import functools
import json
import sys
from collections import defaultdict
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, TypeVar

import click
from more_itertools import seekable

from .serialize import dumps
from .warnings import medium

T = TypeVar("T")

DenyMap = Mapping[str, set[Any]]


def _default_key_func(obj: T) -> str:
    return str(obj)


class DenyList:
    def __init__(self, denylist_file: Path | str) -> None:
        self.file = Path(denylist_file).expanduser().absolute()
        self._deny_raw_list: list[dict[str, Any]] = []
        self._deny_map: DenyMap = defaultdict(set)

        # deny cli, user can override these
        self.fzf_path = None
        self._fzf_options = ()
        self._deny_cli_key_func = None

    def _load(self) -> None:
        if not self.file.exists():
            medium(f"denylist file {self.file} does not exist")
            return

        deny_map: DenyMap = defaultdict(set)
        data: list[dict[str, Any]] = json.loads(self.file.read_text())
        self._deny_raw_list = data

        for ignore in data:
            for k, v in ignore.items():
                deny_map[k].add(v)

        self._deny_map = deny_map

    def load(self) -> DenyMap:
        self._load()
        return self._deny_map

    def write(self) -> None:
        if not self._deny_raw_list:
            medium("no denylist data to write")
            return
        self.file.write_text(json.dumps(self._deny_raw_list))

    @classmethod
    def _is_json_primitive(cls, val: Any) -> bool:
        return isinstance(val, (str, int, float, bool, type(None)))

    @classmethod
    def _stringify_value(cls, val: Any) -> Any:
        # if it's a primitive, just return it
        if cls._is_json_primitive(val):
            return val
        # otherwise, stringify-and-back so we can compare to
        # json data loaded from the denylist file
        return json.loads(dumps(val))

    @classmethod
    def _allow(cls, obj: T, deny_map: DenyMap) -> bool:
        for deny_key, deny_set in deny_map.items():
            # this should be done separately and not as part of the getattr
            # because 'null'/None could actually be a value in the denylist,
            # and the user may define behavior to filter that out
            if not hasattr(obj, deny_key):
                return False
            val = cls._stringify_value(getattr(obj, deny_key))
            # this object doesn't have have the attribute in the denylist
            if val in deny_set:
                return False
        # if we tried all the denylist keys and didn't return False,
        # then this object is allowed
        return True

    def filter(
        self,
        itr: Iterator[T],
        *,
        invert: bool = False,
    ) -> Iterator[T]:
        denyf = functools.partial(self._allow, deny_map=self.load())
        if invert:
            return filter(lambda x: not denyf(x), itr)
        return filter(denyf, itr)

    def deny(self, key: str, value: Any, *, write: bool = False) -> None:
        '''
        add a key/value pair to the denylist
        '''
        if not self._deny_raw_list:
            self._load()
        self._deny_raw({key: self._stringify_value(value)}, write=write)

    def _deny_raw(self, data: dict[str, Any], *, write: bool = False) -> None:
        self._deny_raw_list.append(data)
        if write:
            self.write()

    def _prompt_keys(self, item: T) -> str:
        import pprint

        click.echo(pprint.pformat(item))
        # TODO: extract keys from item by checking if its dataclass/NT etc.?
        resp = click.prompt("Key to deny on").strip()
        if not hasattr(item, resp):
            click.echo(f"Could not find key '{resp}' on item", err=True)
            return self._prompt_keys(item)
        return resp

    def _deny_cli_remember(
        self,
        items: Iterator[T],
        mem: dict[str, T],
    ) -> Iterator[str]:
        # user can override _deny_cli_key_func, so it's not always None, hence the ignore
        keyf = self._deny_cli_key_func or _default_key_func  # type: ignore[redundant-expr]
        # i.e., convert each item to a string, and map str -> item
        for item in items:
            key = keyf(item)
            mem[key] = item
            yield key

    def deny_cli(self, itr: Iterator[T]) -> None:
        try:
            from pyfzf import FzfPrompt
        except ImportError:
            click.echo("pyfzf is required to use the denylist cli, run 'python3 -m pip install pyfzf_iter'", err=True)
            sys.exit(1)

        # wrap in seekable so we can use it multiple times
        # progressively caches the items as we iterate over them
        sit = seekable(itr)

        prompt_continue = True

        while prompt_continue:
            # reset the iterator
            sit.seek(0)
            # so we can map the selected string from fzf back to the original objects
            memory_map: dict[str, T] = {}
            picker = FzfPrompt(executable_path=self.fzf_path, default_options="--no-multi")
            picked_l = picker.prompt(
                self._deny_cli_remember(itr, memory_map),
                "--read0",
                *self._fzf_options,
                delimiter="\0",
            )
            assert isinstance(picked_l, list)
            if picked_l:
                picked: T = memory_map[picked_l[0]]
                key = self._prompt_keys(picked)
                self.deny(key, getattr(picked, key), write=True)
                click.echo(f"Added {self._deny_raw_list[-1]} to denylist", err=True)
            else:
                click.echo("No item selected", err=True)

            prompt_continue = click.confirm("Continue?")
