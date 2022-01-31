"""
Reddit data: saved items/comments/upvotes/etc.
"""
REQUIRES = [
    'git+https://github.com/karlicoss/rexport',
]

from pathlib import Path
from my.core.common import Paths
from dataclasses import dataclass
from typing import Any

from my.config import reddit as uconfig


@dataclass
class reddit(uconfig):
    '''
    Uses [[https://github.com/karlicoss/rexport][rexport]] output.
    '''

    # path[s]/glob to the exported JSON data
    export_path: Paths


from my.core.cfg import make_config, Attrs
# hmm, also nice thing about this is that migration is possible to test without the rest of the config?
def migration(attrs: Attrs) -> Attrs:
    # new structure, take top-level config and extract 'rexport' class
    # previously, 'rexport' key could be location of the rexport repo on disk
    if 'rexport' in attrs and not isinstance(attrs['rexport'], (str, Path)):
        ex: uconfig.rexport = attrs['rexport']
        attrs['export_path'] = ex.export_path
    else:
        from my.core.warnings import high
        high("""DEPRECATED! Please modify your reddit config to look like:

class reddit:
    class rexport:
        export_path: Paths = '/path/to/rexport/data'
            """)
        export_dir = 'export_dir'
        if export_dir in attrs: # legacy name
            attrs['export_path'] = attrs[export_dir]
            high(f'"{export_dir}" is deprecated! Please use "export_path" instead."')
    return attrs

config = make_config(reddit, migration=migration)

###
# TODO not sure about the laziness...

try:
    from rexport import dal
except ModuleNotFoundError as e:
    from my.core.compat import pre_pip_dal_handler
    dal = pre_pip_dal_handler('rexport', e, config, requires=REQUIRES)
# TODO ugh. this would import too early
# but on the other hand we do want to bring the objects into the scope for easier imports, etc. ugh!
# ok, fair enough I suppose. It makes sense to configure something before using it. can always figure it out later..
# maybe, the config could dynamically detect change and reimport itself? dunno.
###

############################

from typing import List, Sequence, Mapping, Iterator, Any
from my.core.common import mcachew, get_files, LazyLogger, make_dict, Stats


logger = LazyLogger(__name__, level='info')


from pathlib import Path
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


Uid        = dal.Sid  # str
Save       = dal.Save
Comment    = dal.Comment
Submission = dal.Submission
Upvote     = dal.Upvote


def _dal() -> dal.DAL:
    inp = list(inputs())
    return dal.DAL(inp)
cache = mcachew(depends_on=inputs, logger=logger) # depends on inputs only


@cache
def saved() -> Iterator[Save]:
    return _dal().saved()


@cache
def comments() -> Iterator[Comment]:
    return _dal().comments()


@cache
def submissions() -> Iterator[Submission]:
    return _dal().submissions()


@cache
def upvoted() -> Iterator[Upvote]:
    return _dal().upvoted()


### the rest of the file is some elaborate attempt of restoring favorite/unfavorite times

from typing import Dict, Iterable, Iterator, NamedTuple
from functools import lru_cache
import pytz
import re
from datetime import datetime
from multiprocessing import Pool

# TODO hmm. apparently decompressing takes quite a bit of time...

class SaveWithDt(NamedTuple):
    save: Save
    backup_dt: datetime

    def __getattr__(self, x):
        return getattr(self.save, x)

# TODO for future events?
EventKind = SaveWithDt


class Event(NamedTuple):
    dt: datetime
    text: str
    kind: EventKind
    eid: str
    title: str
    url: str

    @property
    def cmp_key(self):
        return (self.dt, (1 if 'unfavorited' in self.text else 0))


Url = str

def _get_bdate(bfile: Path) -> datetime:
    RE = re.compile(r'reddit.(\d{14})')
    stem = bfile.stem
    stem = stem.replace('T', '').replace('Z', '') # adapt for arctee
    match = RE.search(stem)
    assert match is not None
    bdt = pytz.utc.localize(datetime.strptime(match.group(1), "%Y%m%d%H%M%S"))
    return bdt


def _get_state(bfile: Path) -> Dict[Uid, SaveWithDt]:
    logger.debug('handling %s', bfile)

    bdt = _get_bdate(bfile)

    saves = [SaveWithDt(save, bdt) for save in dal.DAL([bfile]).saved()]
    return make_dict(
        sorted(saves, key=lambda p: p.save.created),
        key=lambda s: s.save.sid,
    )

# TODO hmm. think about it.. if we set default backups=inputs()
# it's called early so it ends up as a global variable that we can't monkey patch easily
@mcachew(lambda backups: backups)
def _get_events(backups: Sequence[Path], parallel: bool=True) -> Iterator[Event]:
    # todo cachew: let it transform return type? so you don't have to write a wrapper for lists?

    prev_saves: Mapping[Uid, SaveWithDt] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    states: Iterable[Mapping[Uid, SaveWithDt]]
    if parallel:
        with Pool() as p:
            states = p.map(_get_state, backups)
    else:
        # also make it lazy...
        states = map(_get_state, backups)
    # TODO mm, need to make that iterative too?

    for i, (bfile, saves) in enumerate(zip(backups, states)):
        bdt = _get_bdate(bfile)

        first = i == 0

        for key in set(prev_saves.keys()).symmetric_difference(set(saves.keys())):
            ps = prev_saves.get(key, None)
            if ps is not None:
                # TODO use backup date, that is more precise...
                # eh. I guess just take max and it will always be correct?
                assert not first
                yield Event(
                    dt=bdt, # TODO average wit ps.save_dt? 
                    text="unfavorited",
                    kind=ps,
                    eid=f'unf-{ps.sid}',
                    url=ps.url,
                    title=ps.title,
                )
            else: # already in saves
                s = saves[key]
                last_saved = s.backup_dt
                yield Event(
                    dt=s.created if first else last_saved,
                    text=f"favorited{' [initial]' if first else ''}",
                    kind=s,
                    eid=f'fav-{s.sid}',
                    url=s.url,
                    title=s.title,
                )
        prev_saves = saves

    # TODO a bit awkward, favorited should compare lower than unfavorited?

@lru_cache(1)
def events(*args, **kwargs) -> List[Event]:
    inp = inputs()
    # 2.2s for 300 files without cachew
    # 0.2s for 300 files with cachew
    evit = _get_events(inp, *args, **kwargs) # type: ignore[call-arg]
    # todo mypy is confused here and thinks it's iterable of Path? perhaps something to do with mcachew?
    return list(sorted(evit, key=lambda e: e.cmp_key)) # type: ignore[attr-defined,arg-type]


def stats() -> Stats:
    from my.core import stat
    return {
        **stat(saved      ),
        **stat(comments   ),
        **stat(submissions),
        **stat(upvoted    ),
    }


def main() -> None:
    for e in events(parallel=False):
        print(e)


if __name__ == '__main__':
    main()

