from typing import Dict, List, Union, Any, NamedTuple, Tuple, Optional, Iterator, TypeVar
from datetime import datetime
import json
from pathlib import Path
import logging

import pytz

from ..common import get_files

from my_configuration import paths
import my_configuration.repos.ghexport.model as ghexport


def get_logger():
    return logging.getLogger('my.github') # TODO __package__???


class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str
    link: Optional[str]
    body: Optional[str]=None


T = TypeVar('T')
Res = Union[T, Exception]

# TODO split further, title too
def _get_summary(e) -> Tuple[str, Optional[str]]:
    tp = e['type']
    pl = e['payload']
    rname = e['repo']['name']
    if tp == 'ForkEvent':
        url = e['payload']['forkee']['html_url']
        return f"forked {rname}", url
    elif tp == 'PushEvent':
        return f"pushed to {rname}", None
    elif tp == 'WatchEvent':
        return f"watching {rname}", None
    elif tp == 'CreateEvent':
        return f"created {rname}", None
    elif tp == 'PullRequestEvent':
        pr = pl['pull_request']
        action = pl['action']
        link = pr['html_url']
        title = pr['title']
        return f"{action} PR {title}", link
    elif tp == "IssuesEvent":
        action = pl['action']
        iss = pl['issue']
        link = iss['html_url']
        title = iss['title']
        return f"{action} issue {title}", link
    elif tp == "IssueCommentEvent":
        com = pl['comment']
        link = com['html_url']
        iss = pl['issue']
        title = iss['title']
        return f"commented on issue {title}", link
    elif tp == "ReleaseEvent":
        action = pl['action']
        rel = pl['release']
        tag = rel['tag_name']
        link = rel['html_url']
        return f"{action} {rname} [{tag}]", link
    elif tp in (
            "DeleteEvent",
            "PublicEvent",
    ):
        return tp, None # TODO ???
    else:
        return tp, None


def get_model():
    sources = get_files(paths.github.export_dir, glob='*.json')
    model = ghexport.Model(sources)
    return model


def _parse_dt(s: str) -> datetime:
    # TODO isoformat?
    return pytz.utc.localize(datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ'))

def _parse_repository(d: Dict) -> Event:
    name = d['name']
    return Event(
        dt=_parse_dt(d['created_at']),
        summary='created ' + name,
        link=d['url'],
        eid='created_' + name, # TODO ??
    )

def _parse_event(d: Dict) -> Event:
    summary, link = _get_summary(d)
    body = d.get('payload', {}).get('comment', {}).get('body')
    return Event(
        dt=_parse_dt(d['created_at']),
        summary=summary,
        link=link,
        eid=d['id'],
        body=body,
    )


def iter_gdpr_events() -> Iterator[Res[Event]]:
    """
    Parses events from GDPR export (https://github.com/settings/admin)
    """
    files = list(sorted(paths.github.gdpr_dir.glob('*.json')))
    for f in files:
        fn = f.name
        if fn == 'schema.json':
            continue
        elif fn.startswith('repositories_'):
            j = json.loads(f.read_text())
            for r in j:
                try:
                    yield _parse_repository(r)
                except Exception as e:
                    yield e
        else:
            yield RuntimeError(f'Unhandled file: {f}')


def iter_events():
    model = get_model()
    for d in model.events():
        yield _parse_event(d)


# TODO load events from GDPR export?
def get_events():
    return sorted(iter_events(), key=lambda e: e.dt)

# TODO mm. ok, not much point in deserializing as github.Event as it's basically a fancy dict wrapper?
# from github.Event import Event as GEvent # type: ignore
# # see https://github.com/PyGithub/PyGithub/blob/master/github/GithubObject.py::GithubObject.__init__
# e = GEvent(None, None, raw_event, True)


def test():
    events = get_events()
    assert len(events) > 100
    for e in events:
        print(e)
