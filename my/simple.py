'''
Just a demo module for testing and documentation purposes
'''
from dataclasses import dataclass
from typing import Iterator

from my.core import make_config

from my.config import simple as user_config


@dataclass
class simple(user_config):
    count: int


config = make_config(simple)


def items() -> Iterator[int]:
    yield from range(config.count)
