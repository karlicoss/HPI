For code reference, see: [`my.core.denylist.py`](../src/my/core/denylist.py)

A helper module for defining denylists for sources programmatically (in layman's terms, this lets you remove some particular output from a module you don't want)

Lets you specify a class, an attribute to match on,
and a JSON file containing a list of values to deny/filter out

As an example, this will use the `my.ip` module, as filtering incorrect IPs was the original use case for this module:

```python
class IP(NamedTuple):
    addr: str
    dt: datetime
```

A possible denylist file would contain:

```json
[
    {
        "addr": "192.168.1.1",
    },
    {
        "dt": "2020-06-02T03:12:00+00:00",
    }
]
```

Note that if the value being compared to is not a single (non-array/object) JSON primitive
(str, int, float, bool, None), it will be converted to a string before comparison

To use this in code:

```python
from my.ip.all import ips
filtered = DenyList("~/data/ip_denylist.json").filter(ips())
```

To add items to the denylist, in python (in a one-off script):

```python
from my.ip.all import ips
from my.core.denylist import DenyList

d = DenyList("~/data/ip_denylist.json")

for ip in ips():
    # some custom code you define
    if ip.addr == ...:
        d.deny(key="ip", value=ip.ip)
    d.write()
```

... or interactively, which requires [`fzf`](https://github.com/junegunn/fzf) and [`pyfzf-iter`](https://pypi.org/project/pyfzf-iter/) (`python3 -m pip install pyfzf-iter`) to be installed:

```python
from my.ip.all import ips
from my.core.denylist import DenyList

d = DenyList("~/data/ip_denylist.json")
d.deny_cli(ips())  # automatically writes after each selection
```

That will open up an interactive `fzf` prompt, where you can select an item to add to the denylist

This is meant for relatively simple filters, where you want to filter items out
based on a single attribute of a namedtuple/dataclass. If you want to do something
more complex, I would recommend overriding the `all.py` file for that source and
writing your own filter function there.

For more info on all.py:

https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#allpy

This would typically be used in an overridden `all.py` file, or in a one-off script
which you may want to filter out some items from a source, progressively adding more
items to the denylist as you go.

A potential `my/ip/all.py` file might look like (Sidenote: `discord` module from [here](https://github.com/purarue/HPI)):

```python
from typing import Iterator

from my.ip.common import IP
from my.core.denylist import DenyList

deny = DenyList("~/data/ip_denylist.json")

# all possible data from the source
def _ips() -> Iterator[IP]:
    from my.ip import discord
    # could add other imports here

    yield from discord.ips()


# filtered data
def ips() -> Iterator[IP]:
    yield from deny.filter(_ips())
```

To add items to the denylist, you could create a `__main__.py` in your namespace package (in this case, `my/ip/__main__.py`), with contents like:

```python
from my.ip import all

if __name__ == "__main__":
    all.deny.deny_cli(all.ips())
```

Which could then be called like: `python3 -m my.ip`

Or, you could just run it from the command line:

```
python3 -c 'from my.ip import all; all.deny.deny_cli(all.ips())'
```

To edit the `all.py`, you could either:

- install it as editable (`python3 -m pip install --user -e ./HPI`), and then edit the file directly
- or, create a namespace package, which splits the package across multiple directories. For info on that see [`MODULE_DESIGN`](https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#namespace-packages), [`reorder_editable`](https://github.com/purarue/reorder_editable), and possibly the [`HPI-template`](https://github.com/purarue/HPI-template) to create your own HPI namespace package to create your own `all.py` file.

For a real example of this see, [purarue/HPI-personal](https://github.com/purarue/HPI-personal/blob/master/my/ip/all.py)

Sidenote: the reason why we want to specifically override
the all.py and not just create a script that filters out the items you're
not interested in is because we want to be able to import from `my.ip.all`
or `my.location.all` from other modules and get the filtered results, without
having to mix data filtering logic with parsing/loading/caching (the stuff HPI does)
