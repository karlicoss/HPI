"""
Git commits data for repositories on your filesystem
"""

import shutil
import string
from pathlib import Path
from datetime import datetime, timezone
from typing import List, NamedTuple, Optional, Dict, Any, Iterator, Set

from ..core.common import PathIsh, LazyLogger, mcachew, Stats
from ..core.cachew import cache_dir
from ..core.warnings import high

# TODO: create user_config dataclass?
from my.config import commits as config

# pip3 install gitpython
import git # type: ignore
from git.repo.fun import is_git_dir, find_worktree_git_dir # type: ignore


log = LazyLogger('my.commits', level='info')


def by_me(c) -> bool:
    actor = c.author
    if actor.email in config.emails:
        return True
    if actor.name in config.names:
        return True
    return False


class Commit(NamedTuple):
    commited_dt: datetime
    authored_dt: datetime
    message: str
    repo: str # TODO put canonical name here straightaway??
    sha: str
    ref: Optional[str] = None
    # TODO filter so they are authored by me

    @property
    def dt(self) -> datetime:
        return self.commited_dt


# TODO not sure, maybe a better idea to move it to timeline?
def fix_datetime(dt) -> datetime:
    # git module got it's own tzinfo object.. and it's pretty weird
    tz = dt.tzinfo
    assert tz._name == 'fixed'
    offset = tz._offset
    ntz = timezone(offset)
    return dt.replace(tzinfo=ntz)


def _git_root(git_dir: PathIsh) -> Path:
    gd = Path(git_dir)
    if gd.name == '.git':
        return gd.parent
    else:
        return gd # must be bare


def _repo_commits_aux(gr: git.Repo, rev: str, emitted: Set[str]) -> Iterator[Commit]:
    # without path might not handle pull heads properly
    for c in gr.iter_commits(rev=rev):
        if not by_me(c):
            continue
        sha = c.hexsha
        if sha in emitted:
            continue
        emitted.add(sha)

        repo = str(_git_root(gr.git_dir))

        yield Commit(
            commited_dt=fix_datetime(c.committed_datetime),
            authored_dt=fix_datetime(c.authored_datetime),
            message=c.message.strip(),
            repo=repo,
            sha=sha,
            ref=rev,
        )


def repo_commits(repo: PathIsh):
    gr = git.Repo(str(repo))
    emitted: Set[str] = set()
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
    fd_path: Optional[str] = shutil.which("fdfind") or shutil.which("fd-find") or shutil.which("fd")
    if fd_path is None:
        high(f"my.coding.commits requires 'fd' to be installed, See https://github.com/sharkdp/fd#installation")
    # TODO: this just causes it to fail if 'fd' can't be found, but the warning is still sent... seems fine?
    return fd_path or "fd"


# TODO could reuse in clustergit?..
def git_repos_in(roots: List[Path]) -> List[Path]:
    from subprocess import check_output
    outputs = check_output([
        _fd_path(),
        # '--follow', # right, not so sure about follow... make configurable?
        '--hidden',
        '--full-path',
        '--type', 'f',
        '/HEAD', # judging by is_git_dir, it should always be here..
        *roots,
    ]).decode('utf8').splitlines()

    candidates = set(Path(o).resolve().absolute().parent for o in outputs)

    # exclude stuff within .git dirs (can happen for submodules?)
    candidates = {c for c in candidates if '.git' not in c.parts[:-1]}

    candidates = {c for c in candidates if is_git_dir(c)}

    repos = list(sorted(map(_git_root, candidates)))
    return repos


def repos():
    return git_repos_in(config.roots)


# returns modification time for an index to use as hash function
def _repo_depends_on(_repo: Path) -> int:
    for pp in {
        ".git/FETCH_HEAD",
        ".git/HEAD",
        "FETCH_HEAD",  # bare
        "HEAD",  # bare
    }:
        ff = _repo / pp
        if ff.exists():
            return int(ff.stat().st_mtime)
    else:
        raise RuntimeError(f"Could not find a FETCH_HEAD/HEAD file in {_repo}")


def _commits(_repos: List[Path]) -> Iterator[Commit]:
    for r in _repos:
        yield from _cached_commits(r)

_allowed_letters: str = string.ascii_letters + string.digits


def _cached_commits_path(p: Path) -> str:
    # compute a reduced simple filepath using the absolute path of the repo
    simple_path = ''.join(filter(lambda c: c in _allowed_letters, str(p.absolute())))
    return cache_dir() / simple_path / '_cached_commits'


# per-repo commits, to use cachew
@mcachew(
    depends_on=_repo_depends_on,
    logger=log,
    cache_path=lambda p: _cached_commits_path(p)
)
def _cached_commits(repo: Path) -> Iterator[Commit]:
    log.debug('processing %s', repo)
    yield from repo_commits(repo)

def commits() -> Iterator[Commit]:
    return _commits(repos())


def print_all():
    for c in commits():
        print(c)


# TODO enforce read only? although it doesn't touch index
