from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from my.core import Res, Stats, datetime_aware, make_logger, stat, warnings
from my.core.compat import deprecated

logger = make_logger(__name__)


@dataclass
class Watched:
    url: str
    title: str
    when: datetime_aware

    @property
    def eid(self) -> str:
        return f'{self.url}-{self.when.isoformat()}'

    def is_deleted(self) -> bool:
        return self.title == self.url


# todo define error policy?
# although it has one from google takeout module.. so not sure


def watched() -> Iterator[Res[Watched]]:
    emitted: dict[Any, Watched] = {}
    for w in _watched():
        if isinstance(w, Exception):
            yield w  # TODO also make unique?
            continue

        # older exports (e.g. html) didn't have microseconds
        # whereas newer json ones do have them
        # seconds resolution is enough to distinguish watched videos
        # also we're processing takeouts in HPI in reverse order, so first seen watch would contain microseconds, resulting in better data
        without_microsecond = w.when.replace(microsecond=0)

        key = w.url, without_microsecond
        prev = emitted.get(key, None)
        if prev is not None:
            # NOTE: some video titles start with 'Liked ' for liked videos activity
            # but they'd have different timestamp, so fine not to handle them as a special case here
            if w.title in prev.title:
                # often more stuff added to the title, like 'Official Video'
                # in this case not worth emitting the change
                # also handles the case when titles match
                continue
            # otherwise if title changed completely, just emit the change... not sure what else we could do?
            # could merge titles in the 'titles' field and update dynamically? but a bit complicated, maybe later..

            # TODO would also be nice to handle is_deleted here somehow...
            # but for that would need to process data in direct order vs reversed..
            # not sure, maybe this could use a special mode or something?

        emitted[key] = w
        yield w


def _watched() -> Iterator[Res[Watched]]:
    try:
        from google_takeout_parser.models import Activity

        from ..google.takeout.parser import events
    except ModuleNotFoundError as ex:
        logger.exception(ex)
        warnings.high("Please set up my.google.takeout.parser module for better youtube support. Falling back to legacy implementation.")
        yield from _watched_legacy()  # type: ignore[name-defined]
        return

    YOUTUBE_VIDEO_LINK = '://www.youtube.com/watch?v='

    # TODO would be nice to filter, e.g. it's kinda pointless to process Location events
    for e in events():
        if isinstance(e, Exception):
            yield e
            continue

        if not isinstance(e, Activity):
            continue

        url = e.titleUrl

        if url is None:
            continue

        header = e.header

        if header in {'Image Search', 'Search', 'Chrome'}:
            # sometimes results in youtube links.. but definitely not watch history
            continue

        if header not in {'YouTube', 'youtube.com'}:
            # TODO hmm -- wonder if these would end up in dupes in takeout? would be nice to check
            # perhaps this would be easier once we have universal ids
            if YOUTUBE_VIDEO_LINK in url:
                # TODO maybe log in this case or something?
                pass
            continue

        title = e.title

        if header == 'youtube.com' and title.startswith('Visited '):
            continue

        if title.startswith('Searched for') and url.startswith('https://www.youtube.com/results'):
            # search activity, don't need it here
            continue

        if title.startswith('Subscribed to') and url.startswith('https://www.youtube.com/channel/'):
            # todo might be interesting to process somewhere?
            continue

        # all titles contain it, so pointless to include 'Watched '
        # also compatible with legacy titles
        title = title.removeprefix('Watched ')

        # watches originating from some activity end with this, remove it for consistency
        title = title.removesuffix(' - YouTube')

        if YOUTUBE_VIDEO_LINK not in url:
            if 'youtube.com/post/' in url:
                # some sort of channel updates?
                continue
            if 'youtube.com/playlist' in url:
                # 'saved playlist' actions
                continue
            if 'music.youtube.com' in url:
                # todo maybe allow it?
                continue
            if any('From Google Ads' in d for d in e.details):
                # weird, sometimes results in odd urls
                continue

            if title == 'Used YouTube':
                continue

            yield RuntimeError(f'Unexpected url: {e}')
            continue

        # TODO contribute to takeout parser? seems that these still might happen in json data
        title = title.replace("\xa0", " ")

        yield Watched(
            url=url,
            title=title,
            when=e.time,
        )


def stats() -> Stats:
    return stat(watched)


### deprecated stuff (keep in my.media.youtube)

if not TYPE_CHECKING:

    @deprecated("use 'watched' instead")
    def get_watched(*args, **kwargs):
        return watched(*args, **kwargs)

    def _watched_legacy() -> Iterable[Watched]:
        from ..google.takeout.html import read_html
        from ..google.takeout.paths import get_last_takeout

        # todo looks like this one doesn't have retention? so enough to use the last
        path = 'Takeout/My Activity/YouTube/MyActivity.html'
        last = get_last_takeout(path=path)
        if last is None:
            return []

        watches: list[Watched] = []
        for dt, url, title in read_html(last, path):
            watches.append(Watched(url=url, title=title, when=dt))

        # todo hmm they already come sorted.. wonder if should just rely on it..
        return sorted(watches, key=lambda e: e.when)
