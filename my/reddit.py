"""
Reddit data: saved items/comments/upvotes/etc.

Uses [[https://github.com/karlicoss/rexport][rexport]] output.
"""

from typing import Optional
from .core.common import Paths, PathIsh

from types import ModuleType
from my.config import reddit as uconfig
from dataclasses import dataclass

@dataclass
class reddit(uconfig):
    export_path: Paths                     # path[s]/glob to the exported data
    rexport    : Optional[PathIsh] = None  # path to a local clone of rexport

    @property
    def rexport_module(self) -> ModuleType:
        # todo return Type[rexport]??
        # todo ModuleIsh?
        rpath = self.rexport
        if rpath is not None:
            from my.cfg import set_repo
            set_repo('rexport', rpath)

        import my.config.repos.rexport.dal as m
        return m


from .core.cfg import make_config, Attrs
# hmm, also nice thing about this is that migration is possible to test without the rest of the config?
def migration(attrs: Attrs) -> Attrs:
    if 'export_dir' in attrs: # legacy name
        attrs['export_path'] = attrs['export_dir']
    return attrs
config = make_config(reddit, migration=migration)

###
# TODO not sure about the laziness...

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # TODO not sure what is the right way to handle this..
    import my.config.repos.rexport.dal as rexport
else:
    # TODO ugh. this would import too early
    # but on the other hand we do want to bring the objects into the scope for easier imports, etc. ugh!
    # ok, fair enough I suppose. It makes sense to configure something before using it. can always figure it out later..
    # maybe, the config could dynamically detect change and reimport itself? dunno.
    rexport = config.rexport_module
###


from typing import List, Sequence, Mapping, Iterator
from .core.common import mcachew, get_files, LazyLogger, make_dict


logger = LazyLogger(__name__, level='debug')


from pathlib import Path
from .kython.kompress import CPath
def inputs() -> Sequence[Path]:
    files = get_files(config.export_path)
    # TODO Cpath better be automatic by get_files...
    res = list(map(CPath, files)); assert len(res) > 0
    # todo move the assert to get_files?
    return tuple(res)


Sid        = rexport.Sid
Save       = rexport.Save
Comment    = rexport.Comment
Submission = rexport.Submission
Upvote     = rexport.Upvote


def dal() -> rexport.DAL:
    return rexport.DAL(inputs())


@mcachew(hashf=lambda: inputs())
def saved() -> Iterator[Save]:
    return dal().saved()


@mcachew(hashf=lambda: inputs())
def comments() -> Iterator[Comment]:
    return dal().comments()


@mcachew(hashf=lambda: inputs())
def submissions() -> Iterator[Submission]:
    return dal().submissions()


@mcachew(hashf=lambda: inputs())
def upvoted() -> Iterator[Upvote]:
    return dal().upvoted()


### the rest of the file is some elaborate attempt of restoring favorite/unfavorite times

from typing import Dict, Union, Iterable, Iterator, NamedTuple, Any
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
    RE = re.compile(r'reddit-(\d{14})')
    match = RE.search(bfile.stem)
    assert match is not None
    bdt = pytz.utc.localize(datetime.strptime(match.group(1), "%Y%m%d%H%M%S"))
    return bdt


def _get_state(bfile: Path) -> Dict[Sid, SaveWithDt]:
    logger.debug('handling %s', bfile)

    bdt = _get_bdate(bfile)

    saves = [SaveWithDt(save, bdt) for save in rexport.DAL([bfile]).saved()]
    return make_dict(
        sorted(saves, key=lambda p: p.save.created),
        key=lambda s: s.save.sid,
    )

# TODO hmm. think about it.. if we set default backups=inputs()
# it's called early so it ends up as a global variable that we can't monkey patch easily
@mcachew('/L/data/.cache/reddit-events.cache')
def _get_events(backups: Sequence[Path], parallel: bool=True) -> Iterator[Event]:
    # TODO cachew: let it transform return type? so you don't have to write a wrapper for lists?

    prev_saves: Mapping[Sid, SaveWithDt] = {}
    # TODO suppress first batch??
    # TODO for initial batch, treat event time as creation time

    states: Iterable[Mapping[Sid, SaveWithDt]]
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
                    text=f"unfavorited",
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
    evit = _get_events(inputs(), *args, **kwargs)
    return list(sorted(evit, key=lambda e: e.cmp_key))

##


def main() -> None:
    # TODO eh. not sure why but parallel on seems to mess glumov up and cause OOM...
    el = events(parallel=False)
    print(len(el))
    for e in el:
        print(e.text, e.url)
    # for e in get_
    # 509 with urls..
    # for e in get_events():
    #     print(e)


if __name__ == '__main__':
    main()

# TODO deprecate...

get_sources = inputs
get_events = events
