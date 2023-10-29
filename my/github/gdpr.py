"""
Github data (uses [[https://github.com/settings/admin][official GDPR export]])
"""
from dataclasses import dataclass
import json
from pathlib import Path
import tarfile
from typing import Iterable, Any, Sequence, Dict, Optional

from my.core import get_files, Res, PathIsh, stat, Stats, make_logger
from my.core.cfg import make_config
from my.core.error import notnone, echain

from .common import Event, parse_dt, EventIds

# TODO later, use a separate user config? (github_gdpr)
from my.config import github as user_config


@dataclass
class github(user_config):
    gdpr_dir: PathIsh  # path to unpacked GDPR archive


config = make_config(github)


logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    gdir = config.gdpr_dir
    res = get_files(gdir)
    schema_json = [f for f in res if f.name == 'schema.json']
    was_unpacked = len(schema_json) > 0
    if was_unpacked:
        # 'legacy' behaviour, we've been passed an extracted export directory
        # although in principle nothing wrong with running against a directory with several unpacked archives
        # so need to think how to support that in the future as well
        return [schema_json[0].parent]
    # otherwise, should contain a bunch of archives?
    # not sure if need to warn if any of them aren't .tar.gz?
    return res


def events() -> Iterable[Res[Event]]:
    last = max(inputs())

    logger.info(f'extracting data from {last}')

    # a bit naughty and ad-hoc, but we will generify reading from tar.gz. once we have more examples
    # another one is zulip archive
    if last.is_dir():
        files = list(sorted(last.glob('*.json')))  # looks like all files are in the root
        open_file = lambda f: f.open()
    else:
        # treat as .tar.gz
        tfile = tarfile.open(last)
        files = list(sorted(map(Path, tfile.getnames())))
        files = [p for p in files if len(p.parts) == 1 and p.suffix == '.json']
        open_file = lambda p: notnone(tfile.extractfile(f'./{p}'))  # NOTE odd, doesn't work without ./

    # fmt: off
    handler_map = {
        'schema'       : None,
        'issue_events_': None,  # eh, doesn't seem to have any useful bodies
        'attachments_' : None,  # not sure if useful
        'users'        : None,  # just contains random users
        'bots'         : None,  # just contains random bots
        'repositories_'  : _parse_repository,
        'issue_comments_': _parse_issue_comment,
        'issues_'        : _parse_issue,
        'pull_requests_' : _parse_pull_request,
        'projects_'      : _parse_project,
        'releases_'      : _parse_release,
        'commit_comments': _parse_commit_comment,
        ## TODO need to handle these
        'pull_request_review_comments_': None,
        'pull_request_review_threads_': None,
        'pull_request_reviews_': None,
        ##
        'repository_files_': None,  # repository artifacts, probs not very useful
        'discussion_categories_': None,  # doesn't seem to contain any useful info, just some repo metadata
        'organizations_': None,  # no useful info, just some org metadata
    }
    # fmt: on
    for f in files:
        logger.info(f'{f} : processing...')
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

        with open_file(f) as fo:
            j = json.load(fo)
        for r in j:
            try:
                yield handler(r)
            except Exception as e:
                yield echain(RuntimeError(f'While processing file: {f}'), e)


def stats() -> Stats:
    return {
        **stat(events),
    }


# TODO typing.TypedDict could be handy here..
def _parse_common(d: Dict) -> Dict:
    url = d['url']
    body = d.get('body')
    return {
        'dt': parse_dt(d['created_at']),
        'link': url,
        'body': body,
    }


def _parse_repository(d: Dict) -> Event:
    pref = 'https://github.com/'
    url = d['url']
    dts = d['created_at']
    rt = d['type']
    assert url.startswith(pref)
    name = url[len(pref) :]
    eid = EventIds.repo_created(dts=dts, name=name, ref_type=rt, ref=None)
    return Event(
        **_parse_common(d),
        summary='created ' + name,
        eid=eid,
    )


# user may be None if the user was deleted
def _is_bot(user: Optional[str]) -> bool:
    if user is None:
        return False
    return "[bot]" in "user"


def _parse_issue_comment(d: Dict) -> Event:
    url = d['url']
    return Event(
        **_parse_common(d),
        summary=f'commented on issue {url}',
        eid='issue_comment_' + url,
        is_bot=_is_bot(d['user']),
    )


def _parse_issue(d: Dict) -> Event:
    url = d['url']
    title = d['title']
    return Event(
        **_parse_common(d),
        summary=f'opened issue {title}',
        eid='issue_comment_' + url,
        is_bot=_is_bot(d['user']),
    )


def _parse_pull_request(d: Dict) -> Event:
    dts = d['created_at']
    url = d['url']
    title = d['title']
    return Event(
        **_parse_common(d),
        # TODO distinguish incoming/outgoing?
        # TODO action? opened/closed??
        summary=f'opened PR {title}',
        eid=EventIds.pr(dts=dts, action='opened', url=url),
        is_bot=_is_bot(d['user']),
    )


def _parse_project(d: Dict) -> Event:
    url = d['url']
    title = d['name']
    is_bot = "[bot]" in d["creator"]
    # TODO: use columns somehow?
    # Doesn't fit with Event schema,
    # is a list of each of the boards
    return Event(
        **_parse_common(d),
        summary=f'created project {title}',
        eid='project_' + url,
        is_bot=is_bot,
    )


def _parse_release(d: Dict) -> Event:
    tag = d['tag_name']
    return Event(
        **_parse_common(d),
        summary=f'released {tag}',
        eid='release_' + tag,
    )


def _parse_commit_comment(d: Dict) -> Event:
    url = d['url']
    return Event(
        **_parse_common(d),
        summary=f'commented on {url}',
        eid='commit_comment_' + url,
    )
