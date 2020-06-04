"""
Github data: events, comments, etc. (API data)
"""
from dataclasses import dataclass
from typing import Optional

from ..core import Paths, PathIsh

from my.config import github as user_config


@dataclass
class github(user_config):
    '''
    Uses [[https://github.com/karlicoss/ghexport][ghexport]] outputs.
    '''
    # path[s]/glob to the exported JSON data
    export_path: Paths

    # path to a local clone of ghexport
    # alternatively, you can put the repository (or a symlink) in $MY_CONFIG/my/config/repos/ghexport
    ghexport : Optional[PathIsh] = None

    # path to a cache directory
    # if omitted, will use /tmp
    cache_dir: Optional[PathIsh] = None

    @property
    def dal_module(self):
        rpath = self.ghexport
        if rpath is not None:
            from ..core.common import import_dir
            return import_dir(rpath, '.dal')
        else:
            import my.config.repos.ghexport.dal as dal
            return dal
###

# TODO  perhaps using /tmp in case of None isn't ideal... maybe it should be treated as if cache is off

from ..core.cfg import make_config, Attrs
def migration(attrs: Attrs) -> Attrs:
    if 'export_dir' in attrs: # legacy name
        attrs['export_path'] = attrs['export_dir']
    return attrs
config = make_config(github, migration=migration)


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import my.config.repos.ghexport.dal as dal
else:
    dal = config.dal_module

############################

from pathlib import Path
from typing import Tuple, Iterable, Dict, Sequence

from ..core import get_files
from ..core.common import mcachew
from ..kython.kompress import CPath

from .common import Event, parse_dt, Results


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def _dal() -> dal.DAL:
    sources = inputs()
    sources = list(map(CPath, sources)) # TODO maybe move it to get_files? e.g. compressed=True arg?
    return dal.DAL(sources)


# TODO hmm. not good, need to be lazier?...
@mcachew(config.cache_dir, hashf=lambda dal: dal.sources)
def events(dal=_dal()) -> Results:
    for d in dal.events():
        yield _parse_event(d)


def stats():
    from ..core import stat
    return {
        **stat(events),
    }


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


def _parse_event(d: Dict) -> Event:
    summary, link, eid = _get_summary(d)
    if eid is None:
        eid = d['id']
    body = d.get('payload', {}).get('comment', {}).get('body')
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
