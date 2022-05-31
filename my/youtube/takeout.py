from typing import NamedTuple, List, Iterable

from ..core import datetime_aware, Res, LazyLogger
from ..core.compat import removeprefix


logger = LazyLogger(__name__)


class Watched(NamedTuple):
    url: str
    title: str
    when: datetime_aware

    @property
    def eid(self) -> str:
        return f'{self.url}-{self.when.isoformat()}'


# todo define error policy?
# although it has one from google takeout module.. so not sure

def watched() -> Iterable[Res[Watched]]:
    try:
        from ..google.takeout.parser import events
        from google_takeout_parser.models import Activity
    except ModuleNotFoundError as ex:
        logger.exception(ex)
        from ..core.warnings import high
        high("Please set up my.google.takeout.parser module for better youtube support. Falling back to legacy implementation.")
        yield from _watched_legacy()
        return

    YOUTUBE_VIDEO_LINK = '://www.youtube.com/watch?v='

    # TODO would be nice to filter, e.g. it's kinda pointless to process Location events
    for e in events():
        if isinstance(e, Exception):
            yield e

        if not isinstance(e, Activity):
            continue

        url = e.titleUrl
        header = e.header
        title = e.title

        if url is None:
            continue

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

        if header == 'youtube.com' and title.startswith('Visited '):
            continue

        if title.startswith('Searched for') and url.startswith('https://www.youtube.com/results'):
            # search activity, don't need it here
            continue

        if title.startswith('Subscribed to') and url.startswith('https://www.youtube.com/channel/'):
            # todo might be interesting to process somwhere?
            continue

        # all titles contain it, so pointless to include 'Watched '
        # also compatible with legacy titles
        title = removeprefix(title, 'Watched ')

        if YOUTUBE_VIDEO_LINK not in url:
            if e.details == ['From Google Ads']:
                # weird, sometimes results in odd
                continue
            if title == 'Used YouTube' and e.products == ['Android']:
                continue

            yield RuntimeError(f'Unexpected url: {e}')
            continue

        yield Watched(
            url=url,
            title=title,
            when=e.time,
        )


from ..core import stat, Stats
def stats() -> Stats:
    return stat(watched)


### deprecated stuff (keep in my.media.youtube)

get_watched = watched


def _watched_legacy() -> Iterable[Watched]:
    from ..google.takeout.html import read_html
    from ..google.takeout.paths import get_last_takeout

    # todo looks like this one doesn't have retention? so enough to use the last
    path = 'Takeout/My Activity/YouTube/MyActivity.html'
    last = get_last_takeout(path=path)
    if last is None:
        return []

    watches: List[Watched] = []
    for dt, url, title in read_html(last, path):
        watches.append(Watched(url=url, title=title, when=dt))

    # todo hmm they already come sorted.. wonder if should just rely on it..
    return list(sorted(watches, key=lambda e: e.when))
