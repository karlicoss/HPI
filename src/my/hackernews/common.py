from typing import Protocol

from my.core import datetime_aware


def hackernews_link(id: str) -> str:  # noqa: A002
    return f'https://news.ycombinator.com/item?id={id}'


class SavedBase(Protocol):
    @property
    def when(self) -> datetime_aware: ...
    @property
    def uid(self) -> str: ...
    @property
    def url(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def hackernews_link(self) -> str: ...
