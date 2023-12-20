print(f'[main] {__name__} hello')

from typing import Protocol

class Source(Protocol):
    def tweets(self) -> list[str]:
        ...

def merge(*sources: Source) -> list[str]:
    from itertools import chain
    return list(chain.from_iterable(src.tweets() for src in sources))
