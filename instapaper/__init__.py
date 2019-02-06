from datetime import datetime
import json
from pathlib import Path
import pytz
from typing import NamedTuple, Optional

BDIR = Path('/L/backups/instapaper/')

class Highlight(NamedTuple):
    dt: datetime
    hid: str
    text: str
    note: Optional[str]
    url: str
    title: str

def get_files():
    return sorted(f for f in BDIR.iterdir() if f.suffix == '.json')

def get_stuff():
    all_bks = {}
    all_hls = {}
    # TODO can restore url by bookmark id
    for f in get_files():
        with f.open('r') as fo:
            j = json.load(fo)
            # TODO what are bookmarks??
        for b in j['bookmarks']:
            bid = b['bookmark_id']
            prev = all_bks.get(bid, None)
            # assert prev is None or prev == b, '%s vs %s' % (prev, b)
            # TODO shit, ok progress can change apparently
            all_bks[bid] = b
        hls = j['highlights']
        for h in hls:
            hid = h['highlight_id']
            prev = all_hls.get(hid, None)
            assert prev is None or prev == h
            all_hls[hid] = h
    return all_bks, all_hls

def iter_highlights():
    bks, hls = get_stuff()
    for h in hls.values():
        bid = h['bookmark_id']
        bk = bks[bid]
        dt = pytz.utc.localize(datetime.utcfromtimestamp(h['time']))
        yield Highlight(
            hid=str(h['highlight_id']),
            dt=dt,
            text=h['text'],
            note=h['note'],
            url=bk['url'],
            title=bk['title'],
        )

def get_highlights():
    return sorted(iter_highlights(), key=lambda h: h.dt)

def get_todos():
    def is_todo(h):
        return h.note is not None and h.note.lstrip().lower().startswith('todo')
    return list(filter(is_todo, get_highlights()))

def main():
    for h in get_todos():
        print(h)

if __name__ == '__main__':
    main()
