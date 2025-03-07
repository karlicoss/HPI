"""
Github data (uses [[https://github.com/settings/admin][official GDPR export]])
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from my.core import Paths, Res, Stats, get_files, make_logger, stat, warnings
from my.core.compat import add_note
from my.core.json import json_loads

from .common import Event, EventIds, parse_dt

logger = make_logger(__name__)


class config:
    @property
    @abstractmethod
    def gdpr_dir(self) -> Paths:
        raise NotImplementedError


def make_config() -> config:
    # TODO later, use a separate user config? (github_gdpr)
    from my.config import github as user_config

    class combined_config(user_config, config):
        pass

    return combined_config()


def inputs() -> Sequence[Path]:
    gdpr_dir = make_config().gdpr_dir
    res = get_files(gdpr_dir)
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


def events() -> Iterator[Res[Event]]:
    last = max(inputs())

    logger.info(f'extracting data from {last}')

    root: Path | None = None

    if last.is_dir():  # if it's already CPath, this will match it
        root = last
    else:
        try:
            from kompress import CPath

            root = CPath(last)
            assert len(list(root.iterdir())) > 0  # trigger to check if we have the kompress version with targz support
        except Exception as e:
            logger.exception(e)
            warnings.high("Upgrade 'kompress' to latest version with native .tar.gz support. Falling back to unpacking to tmp dir.")

    if root is None:
        from my.core.structure import match_structure

        with match_structure(last, expected=()) as res:  # expected=() matches it regardless any patterns
            [root] = res
            yield from _process_one(root)
    else:
        yield from _process_one(root)


def _process_one(root: Path) -> Iterator[Res[Event]]:
    files = sorted(root.glob('*.json'))  # looks like all files are in the root

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

        j = json_loads(f.read_bytes())
        for r in j:
            try:
                yield handler(r)
            except Exception as e:
                add_note(e, f'^ while processing {f}')
                yield e


def stats() -> Stats:
    return {
        **stat(events),
    }


# TODO typing.TypedDict could be handy here..
def _parse_common(d: dict) -> dict:
    url = d['url']
    body = d.get('body')
    return {
        'dt': parse_dt(d['created_at']),
        'link': url,
        'body': body,
    }


def _parse_repository(d: dict) -> Event:
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
def _is_bot(user: str | None) -> bool:
    if user is None:
        return False
    return "[bot]" in user


def _parse_issue_comment(d: dict) -> Event:
    url = d['url']
    return Event(
        **_parse_common(d),
        summary=f'commented on issue {url}',
        eid='issue_comment_' + url,
        is_bot=_is_bot(d['user']),
    )


def _parse_issue(d: dict) -> Event:
    url = d['url']
    title = d['title']
    return Event(
        **_parse_common(d),
        summary=f'opened issue {title}',
        eid='issue_comment_' + url,
        is_bot=_is_bot(d['user']),
    )


def _parse_pull_request(d: dict) -> Event:
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


def _parse_project(d: dict) -> Event:
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


def _parse_release(d: dict) -> Event:
    tag = d['tag_name']
    return Event(
        **_parse_common(d),
        summary=f'released {tag}',
        eid='release_' + tag,
    )


def _parse_commit_comment(d: dict) -> Event:
    url = d['url']
    return Event(
        **_parse_common(d),
        summary=f'commented on {url}',
        eid='commit_comment_' + url,
    )
