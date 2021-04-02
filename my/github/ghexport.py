"""
Github data: events, comments, etc. (API data)
"""
REQUIRES = [
    'git+https://github.com/karlicoss/ghexport',
]
from dataclasses import dataclass

from my.core import Paths
from my.config import github as user_config


@dataclass
class github(user_config):
    '''
    Uses [[https://github.com/karlicoss/ghexport][ghexport]] outputs.
    '''

    export_path: Paths
    '''path[s]/glob to the exported JSON data'''

###

from my.core.cfg import make_config, Attrs
def migration(attrs: Attrs) -> Attrs:
    export_dir = 'export_dir'
    if export_dir in attrs: # legacy name
        attrs['export_path'] = attrs[export_dir]
        from my.core.warnings import high
        high(f'"{export_dir}" is deprecated! Please use "export_path" instead."')
    return attrs
config = make_config(github, migration=migration)


try:
    from ghexport import dal
except ModuleNotFoundError as e:
    from my.core.compat import pre_pip_dal_handler
    dal = pre_pip_dal_handler('ghexport', e, config, requires=REQUIRES)

############################

from functools import lru_cache
from typing import Tuple, Dict, Sequence, Optional

from my.core import get_files, Path, LazyLogger
from my.core.common import mcachew

from .common import Event, parse_dt, Results, EventIds


logger = LazyLogger(__name__)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def _dal() -> dal.DAL:
    sources = inputs()
    return dal.DAL(sources)


@mcachew(depends_on=lambda: inputs())
def events() -> Results:
    from my.core.common import ensure_unique
    key = lambda e: object() if isinstance(e, Exception) else e.eid
    # crap. sometimes API events can be repeated with exactly the same payload and different id
    # yield from ensure_unique(_events(), key=key)
    yield from _events()


def _events() -> Results:
    dal = _dal()
    for d in dal.events():
        if isinstance(d, Exception):
            yield d
        try:
            yield _parse_event(d)
        except Exception as e:
            yield e


from my.core import stat, Stats
def stats() -> Stats:
    return {
        **stat(events),
    }


@lru_cache(None)
def _log_if_unhandled(e) -> None:
    logger.warning('unhandled event type: %s', e)


# TODO hmm. need some sort of abstract syntax for this...
# TODO split further, title too
Link = str
EventId = str
Body = str
def _get_summary(e) -> Tuple[str, Optional[Link], Optional[EventId], Optional[Body]]:
    # TODO would be nice to give access to raw event within timeline
    dts = e['created_at']
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
        return f"{rname}: forked", url, None, None
    elif tp == 'PushEvent':
        commits = pl['commits']
        messages = [c['message'] for c in commits]
        ref = pl['ref']
        body = '\n'.join(messages)
        eid = f'{tp}_{e["id"]}'
        return f'{rname}: pushed {len(commits)} commits to {ref}', None, eid, body
    elif tp == 'WatchEvent':
        return f"{rname}: watching", None, None, None
    elif tp in mapping:
        what = mapping[tp]
        rt  = pl['ref_type']
        ref = pl['ref']
        if what == 'created':
            # FIXME should handle delection?...
            eid = EventIds.repo_created(dts=dts, name=rname, ref_type=rt, ref=ref)
        mref = '' if ref is None else ' ' + ref
        # todo link to branch? only contains weird API link though
        # TODO combine automatically instead
        return f"{rname}: {what} {rt}{mref}", None, eid, None
    elif tp == 'PullRequestEvent':
        pr = pl['pull_request']
        title = pr['title']

        link  = pr['html_url']
        body  = pr['body']
        action = pl['action']
        eid = EventIds.pr(dts=dts, action=action, url=link)
        return f"{rname}: {action} PR: {title}", link, eid, body
    elif tp == 'PullRequestReviewEvent':
        pr = pl['pull_request']
        title = pr['title']

        rev = pl['review']
        link = rev['html_url']
        body = rev['body']
        eid = f'{tp}_{rev["id"]}'
        return f'{rname}: reviewed PR: {title}', link, eid, body
    elif tp == 'PullRequestReviewCommentEvent':
        pr = pl['pull_request']
        title = pr['title']

        comment = pl['comment']
        link = comment['html_url']
        body = comment['body']
        eid = f'{tp}_{comment["id"]}'
        return f'{rname}: commented on PR: {title}', link, eid, body
    elif tp == 'CommitCommentEvent':
        comment = pl['comment']
        link = comment['html_url']
        body = comment['body']
        eid = f'{tp}_{comment["id"]}'
        cid = comment['commit_id']
        return f'{rname} commented on commit: {cid}', link, eid, body
    elif tp == 'IssuesEvent':
        action = pl['action']
        iss = pl['issue']
        link  = iss['html_url']
        body  = iss['body']
        title = iss['title']
        return f'{rname}: {action} issue: {title}', link, None, body
    elif tp == 'IssueCommentEvent':
        comment = pl['comment']
        link = comment['html_url']
        body = comment['body']
        iss = pl['issue']
        title = iss['title']
        return f'{rname}: commented on issue: {title}', link, 'issue_comment_' + link, body
    elif tp == 'ReleaseEvent':
        action = pl['action']
        rel = pl['release']
        tag = rel['tag_name']
        link = rel['html_url']
        body = rel['body']
        return f"{rname}: {action} [{tag}]", link, None, body
    else:
        _log_if_unhandled(tp)
        return tp, None, None, None


def _parse_event(d: Dict) -> Event:
    summary, link, eid, body = _get_summary(d)
    if eid is None:
        eid = d['id']  # meh
    return Event(
        dt=parse_dt(d['created_at']),
        summary=summary,
        link=link,
        eid=eid,
        body=body,
    )


# TODO mm. ok, not much point in deserializing as github.Event as it's basically a fancy dict wrapper?
# from github.Event import Event as GEvent # type: ignore
# # see https://github.com/PyGithub/PyGithub/blob/master/github/GithubObject.py::GithubObject.__init__
# e = GEvent(None, None, raw_event, True)
