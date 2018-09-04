from kython import load_json_file
from typing import Dict, List, Union, Any, NamedTuple
from datetime import datetime

import os

BPATH = "/L/backups/github-events"

def iter_files():
    for f in os.listdir(BPATH):
        if f.endswith('.json'):
            yield os.path.join(BPATH, f)

def iter_events():
    for f in list(sorted(iter_files())):
        yield f

class Event(NamedTuple):
    dt: datetime
    name: str

def _get_name(e) -> str:
    tp = e['type']
    pl = e['payload']
    rname = e['repo']['name']
    if tp == 'ForkEvent':
        return f"forked {rname}"
    elif tp == 'PushEvent':
        return f"pushed to {rname}"
    elif tp == 'WatchEvent':
        return f"watching {rname}"
    elif tp == 'CreateEvent':
        return f"created {rname}"
    elif tp == 'PullRequestEvent':
        pr = pl['pull_request']
        action = pl['action']
        link = pr['html_url']
        title = pr['title']
        return f"{action} PR {title} {link}"
    elif tp == "IssuesEvent":
        action = pl['action']
        iss = pl['issue']
        link = iss['html_url']
        title = iss['title']
        return f"{action} issue {title} {link}"
    elif tp == "IssueCommentEvent":
        com = pl['comment']
        link = com['html_url']
        iss = pl['issue']
        title = iss['title']
        return f"commented on issue {title} {link}"
    elif tp == "ReleaseEvent":
        action = pl['action']
        rel = pl['release']
        tag = rel['tag_name']
        link = rel['html_url']
        return f"{action} {rname} [{tag}] {link}"
    elif tp in (
            "DeleteEvent",
            "PublicEvent",
    ):
        return tp # TODO ???
    else:
        import ipdb; ipdb.set_trace() 
        return tp

def get_events():
    events: Dict[str, Any] = {}
    for f in iter_events():
        jj = load_json_file(f)
        for e in jj:
            eid = e['id']
            prev = events.get(eid, None)
            if prev is not None:
                if prev != e:
                    raise RuntimeError(f"Mismatch in {e}")
            events[eid] = e
    # TODO utc?? localize
    ev = [Event(
        dt=datetime.strptime(d['created_at'], '%Y-%m-%dT%H:%M:%SZ'),
        name=_get_name(d),
    ) for d in events.values()]
    return sorted(ev, key=lambda e: e.dt)
