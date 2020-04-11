from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Sequence, Any

from .common import get_files

from my.config import pocket as config


def _files():
    return get_files(config.export_path, glob='*.json')


class Highlight(NamedTuple):
    json: Any

    @property
    def text(self) -> str:
        return self.json['quote']

    @property
    def created(self) -> datetime:
        return datetime.strptime(self.json['created_at'], '%Y-%m-%d %H:%M:%S')


class Article(NamedTuple):
    json: Any

    @property
    def url(self) -> str:
        return self.json['given_url']

    @property
    def title(self) -> str:
        return self.json['given_title']

    @property
    def pocket_link(self) -> str:
        return 'https://app.getpocket.com/read/' + self.json['item_id']

    @property
    def added(self) -> datetime:
        return datetime.fromtimestamp(int(self.json['time_added']))

    @property
    def highlights(self) -> Sequence[Highlight]:
        raw = self.json.get('annotations', [])
        return list(map(Highlight, raw))

    # TODO add tags?


def get_articles() -> Sequence[Article]:
    import json
    last = _files()[-1]
    raw = json.loads(last.read_text())['list']
    return list(map(Article, raw.values()))
