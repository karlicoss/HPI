import json
from typing import Dict, List, Union, Any, NamedTuple, Tuple, Optional
from datetime import datetime
from pathlib import Path
import logging


BPATH = Path("/L/backups/github-events")


def get_logger():
    return logging.getLogger('github-provider')


def iter_events():
    for f in list(sorted(BPATH.glob('*.json'))):
        yield f


class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str
    link: Optional[str]


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

def get_events():
    logger = get_logger()

    events: Dict[str, Any] = {}
    for f in iter_events():
        with Path(f).open() as fo:
            jj = json.load(fo)
        for e in jj:
            eid = e['id']
            prev = events.get(eid, None)
            if prev is not None:
                if prev != e:
                    # a = prev['payload']
                    # b = e['payload']
                    # TODO err... push_id has changed??? wtf??
                    logger.error(f"Mismatch in \n{e}\n vs \n{prev}")
            events[eid] = e
    # TODO utc?? localize
    ev = [Event(
        dt=datetime.strptime(d['created_at'], '%Y-%m-%dT%H:%M:%SZ'),
        summary=_get_summary(d)[0],
        link=_get_summary(d)[1],
        eid=d['id'],
    ) for d in events.values()]
    return sorted(ev, key=lambda e: e.dt)


def test():
    assert len(get_events()) > 100
