"""
TODO: move this to doc/DENYLIST ?

A helper module for defining denylists for sources programatically
(in lamens terms, this lets you remove some output from a module you don't want)

Lets you specify a class, an attribute to match on,
and a json file containing a list of values to deny/filter out

As an example, for a class like this:

class IP(NamedTuple):
    ip: str
    dt: datetime

A possible denylist file would contain:

[
    {
        "ip": "192.168.1.1",
    },
    {
        "dt": "2020-06-02T03:12:00+00:00",
    }
]

Note that if the value being compared to is not a single (non-array/object) JSON primitive
(str, int, float, bool, None), it will be converted to a string before comparison

To use this in code:

```
from my.ip.all import ips
filtered = DenyList("~/data/ip_denylist.json").filter(ips())
```

To add items to the denylist, in python (in a one-off script):

```
from my.ip.all import ips
from my.core.denylist import DenyList

d = DenyList("~/data/ip_denylist.json")

for ip in ips():
    # some custom code you define
    if ip.ip == ...:
        d.deny(key="ip", value=ip.ip)
    d.write()
```

... or interactively, which requires `fzf` to be installed, after running

```
from my.ip.all import ips
from my.core.denylist import DenyList

d = DenyList("~/data/ip_denylist.json")
d.deny_cli(ips())
d.write()
```

This is meant for relatively simple filters, where you want to filter out
based on a single attribute of a namedtuple/dataclass. If you want to do something
more complex, I would recommend overriding the all.py file for that source and
writing your own filter function there.

For more info on all.py:
https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#allpy

This would typically be used in an overriden all.py file, or in a one-off script
which you may want to filter out some items from a source, progressively adding more
items to the denylist as you go.

A potential my/ip/all.py file might look like:

```
from typing import Iterator

from my.ip.common import IP  # type: ignore[import]
from my.core.denylist import DenyList

deny = DenyList("~/data/ip_denylist.json")

def ips() -> Iterator[IP]:
    from my.ip import discord

    yield from deny.filter(discord.ips())
```


To add items to the denylist, you could create a __main__.py file, or:

```
python3 -c 'from my.ip import all; all.deny.deny_cli(all.ips())'
```

Sidenote: the reason why we want to specifically override
the all.py and not just create a script that filters out the items you're
not interested in is because we want to be able to import from `my.ip.all`
or `my.location.all` from other modules and get the filtered results, without
having to mix data filtering logic with parsing/loading/caching (the stuff HPI does)
"""

# https://github.com/seanbreckenridge/pyfzf
# TODO: add pip install instructions for this to docs, cant use REQUIRES because
# this a core module and not discovered to be installed with `hpi module install`
REQUIRES = ["pyfzf_iter"]

import json
import functools
from collections import defaultdict
from typing import TypeVar, Set, Any, Mapping, Iterator, Dict, List
from pathlib import Path

import click
from more_itertools import seekable
from my.core.serialize import dumps
from my.core.common import PathIsh
from my.core.warnings import medium


T = TypeVar("T")

DenyMap = Mapping[str, Set[Any]]


def _default_key_func(obj: T) -> str:
    return str(obj)


class DenyList:
    def __init__(self, denylist_file: PathIsh):
        self.file = Path(denylist_file).expanduser().absolute()
        self._deny_raw_list: List[Dict[str, Any]] = []
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
        data: List[Dict[str, Any]]= json.loads(self.file.read_text())
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
        invert: bool = False,
    ) -> Iterator[T]:
        denyf = functools.partial(self._allow, deny_map=self.load())
        if invert:
            return filter(lambda x: not denyf(x), itr)
        return filter(denyf, itr)

    def deny(self, key: str, value: Any, write: bool = False) -> None:
        '''
        add a key/value pair to the denylist
        '''
        if not self._deny_raw_list:
            self._load()
        self._deny_raw({key: self._stringify_value(value)}, write=write)

    def _deny_raw(self, data: Dict[str, Any], write: bool = False) -> None:
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
        mem: Dict[str, T],
    ) -> Iterator[str]:
        keyf = self._deny_cli_key_func or _default_key_func
        # i.e., convert each item to a string, and map str -> item
        for item in items:
            key = keyf(item)
            mem[key] = item
            yield key

    def deny_cli(self, itr: Iterator[T]) -> None:
        from pyfzf import FzfPrompt

        # wrap in seekable so we can use it multiple times
        # progressively caches the items as we iterate over them
        sit = seekable(itr)

        prompt_continue = True

        while prompt_continue:
            # reset the iterator
            sit.seek(0)
            # so we can map the selected string from fzf back to the original objects
            memory_map: Dict[str, T] = {}
            picker = FzfPrompt(
                executable_path=self.fzf_path, default_options="--no-multi"
            )
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
