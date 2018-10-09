from datetime import datetime
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
    aa = actor.email + " " + actor.name
    if actor.email in ('***REMOVED***', '***REMOVED***@gmail.com'):
        return True
    if actor.name in ('***REMOVED***',):
        return True
    for thing in THINGS:
        if thing in aa:
            print("WARNING!!!", actor)
            return True
    return False

class Commit(NamedTuple):
    dt: datetime
    message: str
    repo: str
        # TODO filter so they are authored by me

def iter_commits(repo: str):
    # TODO other branches?
    rr = basename(repo)
    gr = git.Repo(repo)
    for c in gr.head.reference.log():
        if by_me(c.actor):
            yield Commit(
                dt=c.time,
                message=c.message, # TODO strip off 'commit: '? (there are also 'merge')
                repo=rr,
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
                for c in iter_commits(pr):
                    yield c


def get_all_commits():
    ss = set(iter_all_commits())
    return list(sorted(ss, key=lambda c: c.dt))
