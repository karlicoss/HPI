from functools import lru_cache

from ... import paths

@lru_cache()
def ghexport():
    from ...common import import_file
    return import_file(paths.ghexport.repo / 'model.py')


from typing import Dict, List, Union, Any, NamedTuple, Tuple, Optional
from datetime import datetime
from pathlib import Path
import logging

import pytz


def get_logger():
    return logging.getLogger('my.github') # TODO __package__???


class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str
    link: Optional[str]
    body: Optional[str]=None


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
    sources = list(sorted(paths.ghexport.export_dir.glob('*.json')))
    model = ghexport().Model(sources)
    return model


def iter_events():
    model = get_model()
    for d in model.events():
        summary, link = _get_summary(d)
        body = d.get('payload', {}).get('comment', {}).get('body')
        yield Event(
            # TODO isoformat?
            dt=pytz.utc.localize(datetime.strptime(d['created_at'], '%Y-%m-%dT%H:%M:%SZ')),
            summary=summary,
            link=link,
            eid=d['id'],
            body=body,
        )

def get_events():
    return sorted(iter_events(), key=lambda e: e.dt)

# TODO mm. ok, not much point in deserializing as github.Event as it's basically a fancy dict wrapper?
# from github.Event import Event as GEvent # type: ignore
# # see https://github.com/PyGithub/PyGithub/blob/master/github/GithubObject.py::GithubObject.__init__
# e = GEvent(None, None, raw_event, True)


def test():
    assert len(get_events()) > 100
    events = get_events()
    assert len(events) > 100
    for e in events:
        print(e)
