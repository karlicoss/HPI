"""
Github events and their metadata: comments/issues/pull requests
"""
from typing import Dict, Any, NamedTuple, Tuple, Optional, Iterator, TypeVar, Set
from datetime import datetime
import json

import pytz

from ..kython.klogging import LazyLogger
from ..kython.kompress import CPath
from ..common import get_files, mcachew
from ..error import Res

from my.config import github as config
import my.config.repos.ghexport.dal as ghexport


logger = LazyLogger(__name__)


class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str
    link: Optional[str]
    body: Optional[str]=None


# TODO hmm. need some sort of abstract syntax for this...
# TODO split further, title too
def _get_summary(e) -> Tuple[str, Optional[str], Optional[str]]:
    # TODO would be nice to give access to raw event withing timeline
    eid = e['id']
    tp = e['type']
    pl = e['payload']
    rname = e['repo']['name']

    mapping = {
        'CreateEvent': 'created',
        'DeleteEvent': 'deleted',
    }

    if tp == 'ForkEvent':
        url = e['payload']['forkee']['html_url']
        return f"{rname}: forked", url, None
    elif tp == 'PushEvent':
        commits = pl['commits']
        messages = [c['message'] for c in commits]
        body = '\n'.join(messages)
        return f"{rname}: pushed\n{body}", None, None
    elif tp == 'WatchEvent':
        return f"{rname}: watching", None, None
    elif tp in mapping:
        what = mapping[tp]
        rt  = pl['ref_type']
        ref = pl['ref']
        # TODO link to branch? only contains weird API link though
        # TODO hmm. include timestamp instead?
        # breakpoint()
        # TODO combine automatically instead
        return f"{rname}: {what} {rt} {ref}", None, f'{rname}_{what}_{rt}_{ref}_{eid}'
    elif tp == 'PullRequestEvent':
        pr = pl['pull_request']
        action = pl['action']
        link = pr['html_url']
        title = pr['title']
        return f"{rname}: {action} PR {title}", link, f'{rname}_{action}_pr_{link}'
    elif tp == "IssuesEvent":
        action = pl['action']
        iss = pl['issue']
        link = iss['html_url']
        title = iss['title']
        return f"{rname}: {action} issue {title}", link, None
    elif tp == "IssueCommentEvent":
        com = pl['comment']
        link = com['html_url']
        iss = pl['issue']
        title = iss['title']
        return f"{rname}: commented on issue {title}", link, f'issue_comment_' + link
    elif tp == "ReleaseEvent":
        action = pl['action']
        rel = pl['release']
        tag = rel['tag_name']
        link = rel['html_url']
        return f"{rname}: {action} [{tag}]", link, None
    elif tp in 'PublicEvent':
        return f'{tp} {e}', None, None # TODO ???
    else:
        return tp, None, None


def inputs():
   return get_files(config.export_dir)


def _dal():
    sources = inputs()
    sources = list(map(CPath, sources)) # TODO maybe move it to get_files? e.g. compressed=True arg?
    return ghexport.DAL(sources)


def _parse_dt(s: str) -> datetime:
    # TODO isoformat?
    return pytz.utc.localize(datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ'))


# TODO extract to separate gdpr module?
# TODO typing.TypedDict could be handy here..
def _parse_common(d: Dict) -> Dict:
    url = d['url']
    body = d.get('body')
    return {
        'dt'  : _parse_dt(d['created_at']),
        'link': url,
        'body': body,
    }


def _parse_repository(d: Dict) -> Event:
    pref = 'https://github.com/'
    url = d['url']
    assert url.startswith(pref); name = url[len(pref):]
    return Event( # type: ignore[misc]
        **_parse_common(d),
        summary='created ' + name,
        eid='created_' + name, # TODO ??
    )

def _parse_issue_comment(d: Dict) -> Event:
    url = d['url']
    return Event( # type: ignore[misc]
        **_parse_common(d),
        summary=f'commented on issue {url}',
        eid='issue_comment_' + url,
    )


def _parse_issue(d: Dict) -> Event:
    url = d['url']
    title = d['title']
    return Event( # type: ignore[misc]
        **_parse_common(d),
        summary=f'opened issue {title}',
        eid='issue_comment_' + url,
    )


def _parse_pull_request(d: Dict) -> Event:
    url = d['url']
    title = d['title']
    return Event( # type: ignore[misc]
        **_parse_common(d),
        # TODO distinguish incoming/outgoing?
        # TODO action? opened/closed??
        summary=f'opened PR {title}',
        eid='pull_request_' + url,
    )


def _parse_release(d: Dict) -> Event:
    tag = d['tag_name']
    return Event( # type: ignore[misc]
        **_parse_common(d),
        summary=f'released {tag}',
        eid='release_' + tag,
    )


def _parse_commit_comment(d: Dict) -> Event:
    url = d['url']
    return Event( # type: ignore[misc]
        **_parse_common(d),
        summary=f'commented on {url}',
        eid='commoit_comment_' + url,
    )


def _parse_event(d: Dict) -> Event:
    summary, link, eid = _get_summary(d)
    if eid is None:
        eid = d['id']
    body = d.get('payload', {}).get('comment', {}).get('body')
    return Event(
        dt=_parse_dt(d['created_at']),
        summary=summary,
        link=link,
        eid=eid,
        body=body,
    )


def iter_gdpr_events() -> Iterator[Res[Event]]:
    """
    Parses events from GDPR export (https://github.com/settings/admin)
    """
    # TODO allow using archive here?
    files = get_files(config.gdpr_dir, glob='*.json')
    handler_map = {
        'schema'       : None,
        'issue_events_': None, # eh, doesn't seem to have any useful bodies
        'attachments_' : None, # not sure if useful
        'users'        : None, # just contains random users
        'repositories_'  : _parse_repository,
        'issue_comments_': _parse_issue_comment,
        'issues_'        : _parse_issue,
        'pull_requests_' : _parse_pull_request,
        'releases_'      : _parse_release,
        'commit_comments': _parse_commit_comment,
    }
    for f in files:
        handler: Any
        for prefix, h in handler_map.items():
            if not f.name.startswith(prefix):
                continue
            handler = h
            break
        else:
            yield RuntimeError(f'Unhandled file: {f}')
            continue

        if handler is None:
            # ignored
            continue

        j = json.loads(f.read_text())
        for r in j:
            try:
                yield handler(r)
            except Exception as e:
                yield e


# TODO hmm. not good, need to be lazier?...
@mcachew(config.cache_dir, hashf=lambda dal: dal.sources)
def iter_backup_events(dal=_dal()) -> Iterator[Event]:
    for d in dal.events():
        yield _parse_event(d)


def iter_events() -> Iterator[Res[Event]]:
    from itertools import chain
    emitted: Set[Tuple[datetime, str]] = set()
    for e in chain(iter_gdpr_events(), iter_backup_events()):
        if isinstance(e, Exception):
            yield e
            continue
        key = (e.dt, e.eid) # use both just in case
        # TODO wtf?? some minor (e.g. 1 sec) discrepancies (e.g. create repository events)
        if key in emitted:
            logger.debug('ignoring %s: %s', key, e)
            continue
        yield e
        emitted.add(key)


def get_events():
    return sorted(iter_events(), key=lambda e: e.dt)

# TODO mm. ok, not much point in deserializing as github.Event as it's basically a fancy dict wrapper?
# from github.Event import Event as GEvent # type: ignore
# # see https://github.com/PyGithub/PyGithub/blob/master/github/GithubObject.py::GithubObject.__init__
# e = GEvent(None, None, raw_event, True)
