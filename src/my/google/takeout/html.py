'''
Google Takeout exports: browsing history, search/youtube/google play activity
'''

from __future__ import annotations

from my.core import __NOT_HPI_MODULE__  # isort: skip

import re
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote

import pytz

from my.core.time import abbr_to_timezone

# NOTE: https://bugs.python.org/issue22377 %Z doesn't work properly
_TIME_FORMATS = [
    "%b %d, %Y, %I:%M:%S %p",  # Mar 8, 2018, 5:14:40 PM
    "%d %b %Y, %H:%M:%S",
]


# ugh. something is seriously wrong with datetime, it wouldn't parse timezone aware UTC timestamp :(
def parse_dt(s: str) -> datetime:
    end = s[-3:]
    tz: Any # meh
    if end == ' PM' or end == ' AM':
        # old takeouts didn't have timezone
        # hopefully it was utc? Legacy, so no that much of an issue anymore..
        # todo although maybe worth adding timezone from location provider?
        # note: need to use pytz here for localize call later
        tz = pytz.utc
    else:
        s, tzabbr = s.rsplit(maxsplit=1)
        tz = abbr_to_timezone(tzabbr)

    dt: datetime | None = None
    for fmt in _TIME_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        raise RuntimeError("None of formats {} matched {}", _TIME_FORMATS, dt)
    return tz.localize(dt)


def test_parse_dt() -> None:
    parse_dt('Jun 23, 2015, 2:43:45 PM')
    parse_dt('Jan 25, 2019, 8:23:48 AM GMT')
    parse_dt('Jan 22, 2020, 8:34:00 PM UTC')
    parse_dt('Sep 10, 2019, 8:51:45 PM MSK')

    # this testcases are interesting: in pytz, abbr resolution might depend on the _current_ date!
    # so these used to fail during winter
    # you can see all the different values used in in _tzinfos field
    parse_dt('Jun 01, 2018, 11:00:00 PM BST')
    parse_dt('Jun 01, 2018, 11:00:00 PM PDT')
    parse_dt('Feb 01, 2018, 11:00:00 PM PST')

    parse_dt('6 Oct 2020, 14:32:28 PDT')


class State(Enum):
    OUTSIDE = 0
    INSIDE = 1
    PARSING_LINK = 2
    PARSING_DATE = 3


Url = str
Title = str
Parsed = tuple[datetime, Url, Title]
Callback = Callable[[datetime, Url, Title], None]


# would be easier to use beautiful soup, but ends up in a big memory footprint..
class TakeoutHTMLParser(HTMLParser):
    def __init__(self, callback: Callback) -> None:
        super().__init__()
        self.state: State = State.OUTSIDE

        self.title_parts: list[str] = []
        self.title: str | None = None
        self.url: str | None = None

        self.callback = callback

    # enter content cell -> scan link -> scan date -> finish till next content cell
    def handle_starttag(self, tag, attrs):
        if self.state == State.INSIDE and tag == 'a':
            self.state = State.PARSING_LINK
            [hr] = (v for k, v in attrs if k == 'href')
            assert hr is not None

            # sometimes it's starts with this prefix, it's apparently clicks from google search? or visits from chrome address line? who knows...
            # TODO handle http?
            prefix = r'https://www.google.com/url?q='
            if hr.startswith(prefix + "http"):
                hr = hr[len(prefix):]
                hr = unquote(hr) # TODO not sure about that...
            assert self.url is None; self.url = hr

    def handle_endtag(self, tag):
        if self.state == State.PARSING_LINK and tag == 'a':
            assert self.title is None
            assert len(self.title_parts) > 0
            self.title = ''.join(self.title_parts)
            self.title_parts = []

            self.state = State.PARSING_DATE

    # search example:
    # Visited Emmy Noether - Wikipedia
    # Dec 17, 2018, 8:16:18 AM UTC

    # youtube example:
    # Watched Jamie xx - Gosh
    # JamiexxVEVO
    # Jun 21, 2018, 5:48:34 AM
    # Products:
    #  YouTube
    def handle_data(self, data):
        if self.state == State.OUTSIDE:
            if data[:-1].strip() in ("Watched", "Visited"):
                self.state = State.INSIDE
                return

        if self.state == State.PARSING_LINK:
            self.title_parts.append(data)
            return

        # TODO extracting channel as part of wereyouhere could be useful as well
        # need to check for regex because there might be some stuff in between
        if self.state == State.PARSING_DATE and re.search(r'\d{4}.*:.*:', data):
            time = parse_dt(data.strip())
            assert time.tzinfo is not None

            assert self.url is not None; assert self.title is not None
            self.callback(time, self.url, self.title)
            self.url = None; self.title = None

            self.state = State.OUTSIDE
            return


def read_html(tpath: Path, file: str) -> Iterable[Parsed]:
    results: list[Parsed] = []
    def cb(dt: datetime, url: Url, title: Title) -> None:
        results.append((dt, url, title))
    parser = TakeoutHTMLParser(callback=cb)
    with (tpath / file).open() as fo:
        data = fo.read()
        parser.feed(data)
    return results
