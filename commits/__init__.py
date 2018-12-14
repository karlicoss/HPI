from datetime import datetime, timezone
from typing import List, NamedTuple, Optional
from os.path import basename, islink, isdir, join
from os import listdir

import git # type: ignore

# TODO do something smarter... later
# TODO def run against bitbucket and gh backups
SOURCES = [
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
]

THINGS = [
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
    '***REMOVED***',
]

def by_me(actor):
    if actor.email in ('***REMOVED***', '***REMOVED***@gmail.com'):
        return True
    if actor.name in ('***REMOVED***',):
        return True
    aa = f"{actor.email} {actor.name}"
    for thing in THINGS:
        if thing in aa:
            print("WARNING!!!", actor)
            return True
    return False

class Commit(NamedTuple):
    dt: datetime
    message: str
    repo: str
    sha: str
        # TODO filter so they are authored by me

# TODO not sure, maybe a better idea to move it to timeline?
def fix_datetime(dt) -> datetime:
    # git module got it's own tzinfo object.. and it's pretty weird
    tz = dt.tzinfo
    assert tz._name == 'fixed'
    offset = tz._offset
    ntz = timezone(offset)
    return dt.replace(tzinfo=ntz)


def iter_commits(repo: str):
    # TODO other branches?
    rr = basename(repo)
    gr = git.Repo(repo)
    for c in gr.iter_commits():
        if by_me(c.author):
            yield Commit(
                dt=fix_datetime(c.committed_datetime), # TODO authored??
                message=c.message.strip(),
                repo=rr,
                sha=c.hexsha,
            )

def is_git_repo(d: str):
    dotgit = join(d, '.git')
    return isdir(dotgit)

# TODO eh. traverse all of filesystem?? or only specific dirs for now?
def iter_all_commits():
    for src in SOURCES:
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


def get_all_commits():
    res = {}
    for c in iter_all_commits():
        nn = res.get(c.sha, None)
        if nn is None:
            res[c.sha] = c
        else:
            res[c.sha] = min(nn, c, key=lambda c: c.sha)

    return list(sorted(res.values(), key=lambda c: c.dt))
