from datetime import datetime, timezone
from typing import List, NamedTuple, Optional, Dict, Any, Iterator
from pathlib import Path
from os.path import basename, islink, isdir, join
from os import listdir

from kython.ktyping import PathIsh

# pip3 install gitpython
import git # type: ignore

# TODO do something smarter... later
# TODO def run against bitbucket and gh backups
# TODO github/bitbucket repos?
# TODO FIXME syncthing? or not necessary with coding view??
SOURCES = [
    '***REMOVED***',
    # '***REMOVED***',
    # '***REMOVED***',
    '***REMOVED***',
]

THINGS = [
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
]

def by_me(c):
    actor = c.author
    if actor.email in ('***REMOVED***', '***REMOVED***@gmail.com'):
        return True
    if actor.name in ('***REMOVED***',):
        return True
    aa = f"{actor.email} {actor.name}"
    for thing in THINGS:
        if thing in aa:
            print("WARNING!!!", actor, c, c.repo)
            return True
    return False

class Commit(NamedTuple):
    commited_dt: datetime
    authored_dt: datetime
    message: str
    repo: str
    sha: str
    ref: Optional[str]=None
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

from kython.ktyping import PathIsh

def iter_commits(repo: PathIsh, ref=None):
    # TODO other branches?
    repo = Path(repo)
    rr = repo.name
    gr = git.Repo(repo)
    # without path might not handle pull heads properly
    for c in gr.iter_commits(rev=None if ref is None else ref.path):
        if by_me(c):
            yield Commit(
                commited_dt=fix_datetime(c.committed_datetime),
                authored_dt=fix_datetime(c.authored_datetime),
                message=c.message.strip(),
                repo=rr,
                sha=c.hexsha,
                ref=ref,
            )

def iter_all_ref_commits(repo: Path):
    gr = git.Repo(str(repo))
    for r in gr.references:
        yield from iter_commits(repo=repo, ref=r)


def is_git_repo(d: str):
    dotgit = join(d, '.git')
    return isdir(dotgit)

from git.repo.fun import is_git_dir # type: ignore

def iter_all_git_repos(dd: PathIsh) -> Iterator[Path]:
    # TODO would that cover all repos???
    dd = Path(dd)
    assert dd.exists()
    for xx in dd.glob('**/HEAD'): # ugh
        c = xx.parent
        if not is_git_dir(c):
            continue
        if c.name == '.git':
            c = c.parent
        yield c


def canonical_name(repo: Path) -> str:
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
    pass


# TODO is it only used in wcommits?
def iter_multi_commits(sources):
    for src in sources:
        # TODO warn if doesn't exist?
        for d in listdir(src):
            pr = join(src, d)
            if is_git_repo(pr):
                try:
                    for c in iter_commits(pr):
                        yield c
                except ValueError as ve:
                    if "Reference at 'refs/heads/master' does not exist" in str(ve):
                        continue # TODO wtf??? log?
                    else:
                        raise ve

# TODO eh. traverse all of filesystem?? or only specific dirs for now?
def iter_all_commits():
    return iter_multi_commits(SOURCES)


def get_all_commits():
    res: Dict[str, Any] = {}
    for c in iter_all_commits():
        nn = res.get(c.sha, None)
        if nn is None:
            res[c.sha] = c
        else:
            res[c.sha] = min(nn, c, key=lambda c: c.sha)

    return list(sorted(res.values(), key=lambda c: c.dt))


def main():
    for c in get_all_commits(): # ('***REMOVED***'):
        print(c)


if __name__ == '__main__':
    main()
