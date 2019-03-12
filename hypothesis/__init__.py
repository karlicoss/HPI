from functools import lru_cache
from kython import listdir_abs
from typing import Dict, List, NamedTuple, Optional
from pathlib import Path
import json
from pytz import UTC
from datetime import datetime
import os

from kython import group_by_key
from kython.misc import the

_PATH = '/L/backups/hypothesis/'

class Entry(NamedTuple):
    dt: datetime
    summary: str
    content: Optional[str] # might be none if for instance we just marked page with tags. not sure if we want to handle it somehow separately
    link: str
    eid: str
    annotation: Optional[str]
    context: str
    tags: List[str]

Url = str

class Page(NamedTuple):
    highlights: List[Entry]

    @property
    # @lru_cache()
    def url(self):
        return the(h.url for h in self.highlights)

    @property
    # @lru_cache()
    def title(self):
        return the(h.title for h in self.highlights)

    @property
    # @lru_cache()
    # TODO shit. can't be cached because of self, wtf??? how to get around it??
    def dt(self):
        return min(h.dt for h in self.highlights)


# TODO guarantee order?
def _iter():
    last = max(listdir_abs(_PATH))
    with Path(last).open() as fo:
        j = json.load(fo)
    for i in j:
        dts = i['created']
        title = ' '.join(i['document']['title'])
        selectors = i['target'][0].get('selector', None)
        if selectors is None:
            # TODO warn?...
            selectors = []
        content: Optional[str]
        for s in selectors:
            if 'exact' in s:
                content = s['exact']
                break
        eid = i['id']
        link = i['uri']
        dt = datetime.strptime(dts[:-3] + dts[-2:], '%Y-%m-%dT%H:%M:%S.%f%z')
        txt = i['text']
        annotation = None if len(txt.strip()) == 0 else txt
        context = i['links']['incontext']
        yield Entry(
            dt,
            title,
            content,
            link,
            eid,
            annotation=annotation,
            context=context,
            tags=i['tags'],
        )


def get_pages() -> List[Page]:
    grouped = group_by_key(_iter(), key=lambda e: e.link)
    pages = []
    for link, group in grouped.items():
        group = list(sorted(group, key=lambda e: e.dt))
        pages.append(Page(highlights=group))
    pages = list(sorted(pages, key=lambda p: p.dt))
    # TODO fixme page tag??
    return pages


def get_entries():
    return list(_iter())


def get_todos():
    def is_todo(e: Entry) -> bool:
        if any(t.lower() == 'todo' for t in  e.tags):
            return True
        if e.annotation is None:
            return False
        return e.annotation.lstrip().lower().startswith('todo')
    return list(filter(is_todo, get_entries()))

def _main():
    for page in get_pages():
        print(page)

if __name__ == '__main__':
    _main()
