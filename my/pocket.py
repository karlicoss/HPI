from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Sequence, Any

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


# TODO integrate with mycfg
def get_articles(json_path: Path) -> Sequence[Article]:
    import json
    raw = json.loads(json_path.read_text())['list']
    return list(map(Article, raw.values()))
