import sys
from datetime import UTC, datetime
from types import ModuleType

import pytest
from google_takeout_parser.models import Activity

from my.youtube.takeout import Watched, _is_youtube_video_url, _watched


def _activity(*, title: str, url: str) -> Activity:
    return Activity(
        header='YouTube',
        title=title,
        time=datetime(2026, 7, 18, tzinfo=UTC),
        description=None,
        titleUrl=url,
        subtitles=[],
        details=[],
        locationInfos=[],
        products=['YouTube'],
    )


def test_youtube_video_urls() -> None:
    assert _is_youtube_video_url('https://www.youtube.com/watch?v=video')
    assert _is_youtube_video_url('https://youtube.com/watch?v=video')
    assert _is_youtube_video_url('https://m.youtube.com/watch?v=video')
    assert _is_youtube_video_url('https://www.youtube.com/shorts/short')
    assert _is_youtube_video_url('https://www.youtube.com/watch?v=')
    assert not _is_youtube_video_url('https://www.youtube.com/watch')
    assert not _is_youtube_video_url('https://example.com/watch?v=video')


@pytest.mark.parametrize('scheme', ['http', 'https'])
@pytest.mark.parametrize('title_scheme', ['http', 'https'])
def test_is_deleted_url_placeholder(*, scheme: str, title_scheme: str) -> None:
    """The parser may upgrade the URL to HTTPS while leaving an HTTP URL in the title."""
    watched = Watched(
        url=f'{scheme}://www.youtube.com/watch?v=video',
        title=f'{title_scheme}://www.youtube.com/watch?v=video',
        when=datetime(2026, 7, 18, tzinfo=UTC),
    )
    assert watched.is_deleted()


@pytest.mark.parametrize(
    'title',
    [
        'A regular video',
        'http://www.youtube.com/watch?v=another',
        'http://example.com/watch?v=video',
        'ftp://www.youtube.com/watch?v=video',
    ],
)
def test_is_deleted_requires_same_url(*, title: str) -> None:
    """Normalizing HTTP/HTTPS must not mistake real titles or different URLs for placeholders."""
    watched = Watched(
        url='https://www.youtube.com/watch?v=video',
        title=title,
        when=datetime(2026, 7, 18, tzinfo=UTC),
    )
    assert not watched.is_deleted()


def test_watched_filters_non_watch_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    activities = [
        _activity(title='Watched A regular video', url='https://www.youtube.com/watch?v=video'),
        _activity(title='Watched A short', url='https://www.youtube.com/shorts/short'),
        _activity(title='Shared video', url='https://youtube.com/watch?v=shared'),
        _activity(title='Shared shorts', url='https://youtube.com/shorts/shared'),
        _activity(title='Joined YouTube Music', url='https://www.youtube.com'),
        _activity(
            title='Visited an advertiser',
            url='https://www.google.com/url?q=https://example.com',
        ),
    ]
    parser = ModuleType('my.google.takeout.parser')
    setattr(parser, 'events', lambda: iter(activities))
    monkeypatch.setitem(sys.modules, 'my.google.takeout.parser', parser)

    results = list(_watched())

    assert all(isinstance(result, Watched) for result in results)
    assert [(result.title, result.url) for result in results if isinstance(result, Watched)] == [
        ('A regular video', 'https://www.youtube.com/watch?v=video'),
        ('A short', 'https://www.youtube.com/shorts/short'),
    ]
