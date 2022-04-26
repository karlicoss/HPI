"""
An example all.py stub module that provides ip data

To use this, you'd add IP providers that yield IPs to the 'ips' function

For an example of how this could be used, see https://github.com/seanbreckenridge/HPI/tree/master/my/ip
"""

REQUIRES = ["git+https://github.com/seanbreckenridge/ipgeocache"]


from typing import Iterator

from my.core.common import Stats, warn_if_empty

from .common import IP


@warn_if_empty
def ips() -> Iterator[IP]:
    yield from ()


def stats() -> Stats:
    from my.core import stat

    return {
        **stat(ips),
    }
