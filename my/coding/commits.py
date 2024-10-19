"""
Git commits data for repositories on your filesystem
"""

from __future__ import annotations

REQUIRES = [
    'gitpython',
]

import shutil
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, cast

from my.core import LazyLogger, PathIsh, make_config
from my.core.cachew import cache_dir, mcachew
from my.core.warnings import high

from my.config import commits as user_config  # isort: skip


@dataclass
class commits_cfg(user_config):
    roots: Sequence[PathIsh] = field(default_factory=list)
    emails: Sequence[str] | None = None
    names: Sequence[str] | None = None


# experiment to make it lazy?
# would be nice to have a nicer syntax for it... maybe make_config could return a 'lazy' object
def config() -> commits_cfg:
    res = make_config(commits_cfg)
    if res.emails is None and res.names is None:
        # todo error policy? throw/warn/ignore
        high("Set either 'emails' or 'names', otherwise you'll get no commits")
    return res

##########################

import git
from git.repo.fun import is_git_dir

log = LazyLogger(__name__, level='info')


def by_me(c: git.objects.commit.Commit) -> bool:
    actor = c.author
    if actor.email in (config().emails or ()):
        return True
    if actor.name in (config().names or ()):
        return True
    return False


@dataclass
class Commit:
    committed_dt: datetime
    authored_dt: datetime
    message: str
    repo: str # TODO put canonical name here straight away??
    sha: str
    ref: Optional[str] = None
    # TODO filter so they are authored by me

    @property
    def dt(self) -> datetime:
        return self.committed_dt

    # for backwards compatibility, was misspelled previously
    @property
    def commited_dt(self) -> datetime:
        high("DEPRECATED! Please replace 'commited_dt' with 'committed_dt' (two 't's instead of one)")
        return self.committed_dt


# TODO not sure, maybe a better idea to move it to timeline?
def fix_datetime(dt: datetime) -> datetime:
    # git module got it's own tzinfo object.. and it's pretty weird
    tz = dt.tzinfo
    assert tz is not None, dt
    assert getattr(tz, '_name') == 'fixed'
    offset = getattr(tz, '_offset')
    ntz = timezone(offset)
    return dt.replace(tzinfo=ntz)


def _git_root(git_dir: PathIsh) -> Path:
    gd = Path(git_dir)
    if gd.name == '.git':
        return gd.parent
    else:
        return gd # must be bare


def _repo_commits_aux(gr: git.Repo, rev: str, emitted: set[str]) -> Iterator[Commit]:
    # without path might not handle pull heads properly
    for c in gr.iter_commits(rev=rev):
        if not by_me(c):
            continue
        sha = c.hexsha
        if sha in emitted:
            continue
        emitted.add(sha)

        # todo figure out how to handle Union[str, PathLike[Any]].. should it be part of PathIsh?
        repo = str(_git_root(gr.git_dir)) # type: ignore[arg-type]

        yield Commit(
            committed_dt=fix_datetime(c.committed_datetime),
            authored_dt=fix_datetime(c.authored_datetime),
            # hmm no idea why is it typed with Union[str, bytes]??
            # https://github.com/gitpython-developers/GitPython/blob/1746b971387eccfc6fb4e34d3c334079bbb14b2e/git/objects/commit.py#L214
            message=cast(str, c.message).strip(),
            repo=repo,
            sha=sha,
            ref=rev,
        )


def repo_commits(repo: PathIsh):
    gr = git.Repo(str(repo))
    emitted: set[str] = set()
    for r in gr.references:
        yield from _repo_commits_aux(gr=gr, rev=r.path, emitted=emitted)


def canonical_name(repo: Path) -> str:
    # TODO could determine origin?
    if repo.match('github/repositories/*/repository'):
        return repo.parent.name
    else:
        return repo.name
        # if r.name == 'repository': # 'repository' thing from github..
        #     rname = r.parent.name
        # else:
        #     rname = r.name
    # if 'backups/github' in repo:
    #     pass # TODO


def _fd_path() -> str:
    # todo move it to core
    fd_path: str | None = shutil.which("fdfind") or shutil.which("fd-find") or shutil.which("fd")
    if fd_path is None:
        high("my.coding.commits requires 'fd' to be installed, See https://github.com/sharkdp/fd#installation")
    assert fd_path is not None
    return fd_path


def git_repos_in(roots: list[Path]) -> list[Path]:
    from subprocess import check_output
    outputs = check_output([
        _fd_path(),
        # '--follow', # right, not so sure about follow... make configurable?
        '--hidden',
        '--no-ignore',  # otherwise doesn't go inside .git directory (from fd v9)
        '--full-path',
        '--type', 'f',
        '/HEAD', # judging by is_git_dir, it should always be here..
        *roots,
    ]).decode('utf8').splitlines()

    candidates = {Path(o).resolve().absolute().parent for o in outputs}

    # exclude stuff within .git dirs (can happen for submodules?)
    candidates = {c for c in candidates if '.git' not in c.parts[:-1]}

    candidates = {c for c in candidates if is_git_dir(c)}

    repos = sorted(map(_git_root, candidates))
    return repos


def repos() -> list[Path]:
    return git_repos_in(list(map(Path, config().roots)))


# returns modification time for an index to use as hash function
def _repo_depends_on(_repo: Path) -> int:
    for pp in [
        ".git/FETCH_HEAD",
        ".git/HEAD",
        "FETCH_HEAD",  # bare
        "HEAD",  # bare
    ]:
        ff = _repo / pp
        if ff.exists():
            return int(ff.stat().st_mtime)
    raise RuntimeError(f"Could not find a FETCH_HEAD/HEAD file in {_repo}")


def _commits(_repos: list[Path]) -> Iterator[Commit]:
    for r in _repos:
        yield from _cached_commits(r)


def _cached_commits_path(p: Path) -> str:
    p = cache_dir() / 'my.coding.commits:_cached_commits' / str(p.absolute()).strip("/")
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


# per-repo commits, to use cachew
@mcachew(
    depends_on=_repo_depends_on,
    logger=log,
    cache_path=_cached_commits_path,
)
def _cached_commits(repo: Path) -> Iterator[Commit]:
    log.debug('processing %s', repo)
    yield from repo_commits(repo)


def commits() -> Iterator[Commit]:
    return _commits(repos())


# TODO enforce read only? although it doesn't touch index
