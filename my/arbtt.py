'''
[[https://github.com/nomeata/arbtt#arbtt-the-automatic-rule-based-time-tracker][Arbtt]] time tracking
'''

REQUIRES = ['ijson', 'cffi']
# NOTE likely also needs libyajl2 from apt or elsewhere?


from pathlib import Path
from typing import Sequence, Iterable, List, Optional


def inputs() -> Sequence[Path]:
    try:
        from my.config import arbtt as user_config
    except ImportError:
        from .core.warnings import low
        low("Couldn't find 'arbtt' config section, falling back to the default capture.log (usually in HOME dir). Add 'arbtt' section with logfiles = '' to suppress this warning.")
        return []
    else:
        from .core import get_files
        return get_files(user_config.logfiles)


from .core import dataclass, Json, PathIsh, datetime_aware
from .core.common import isoparse


@dataclass
class Entry:
    '''
    For the format reference, see
    https://github.com/nomeata/arbtt/blob/e120ad20b9b8e753fbeb02041720b7b5b271ab20/src/DumpFormat.hs#L39-L46
    '''

    json: Json
    # inactive time -- in ms

    @property
    def dt(self) -> datetime_aware:
        # contains utc already
        ds = self.json['date']
        elen = 27
        lds = len(ds)
        if lds < elen:
            # ugh. sometimes contains less that 6 decimal points
            ds = ds[:-1] + '0' * (elen - lds) + 'Z'
        elif lds > elen:
            # ahd sometimes more...
            ds = ds[:elen - 1] + 'Z'

        return isoparse(ds)

    @property
    def active(self) -> Optional[str]:
        # NOTE: WIP, might change this in the future...
        ait = (w for w in self.json['windows'] if w['active'])
        a = next(ait, None)
        if a is None:
            return None
        a2 = next(ait, None)
        assert a2 is None, a2 # hopefully only one can be active in a time?

        p = a['program']
        t = a['title']
        # todo perhaps best to keep it structured, e.g. for influx
        return f'{p}: {t}'


# todo multiple threads? not sure if would help much... (+ need to find offset somehow?)
def entries() -> Iterable[Entry]:
    inps = list(inputs())

    base: List[PathIsh] = ['arbtt-dump', '--format=json']

    cmds: List[List[PathIsh]]
    if len(inps) == 0:
        cmds = [base] # rely on default
    else:
        # otherwise, 'merge' them
        cmds = [base + ['--logfile', f] for f in inps]

    import ijson.backends.yajl2_cffi as ijson # type: ignore
    from subprocess import Popen, PIPE
    for cmd in cmds:
        with Popen(cmd, stdout=PIPE) as p:
            out = p.stdout; assert out is not None
            for json in ijson.items(out, 'item'):
                yield Entry(json=json)


def fill_influxdb() -> None:
    from .core.influxdb import magic_fill
    from .core.freezer import Freezer
    freezer = Freezer(Entry)
    fit = (freezer.freeze(e) for e in entries())
    # TODO crap, influxdb doesn't like None https://github.com/influxdata/influxdb/issues/7722
    # wonder if can check it statically/warn?
    fit = (f for f in fit if f.active is not None)

    # todo could tag with computer name or something...
    # todo should probably also tag with 'program'?
    magic_fill(fit, name=f'{entries.__module__}:{entries.__name__}')


from .core import stat, Stats
def stats() -> Stats:
    return stat(entries)
