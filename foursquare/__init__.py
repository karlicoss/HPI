from datetime import datetime, timezone, timedelta
# TODO pytz for timezone???
from typing import List, Dict, NamedTuple, Union, Any, Tuple

from kython import safe_get, flatten, load_json_file
from kython.data import get_last_file

# TODO actually i'm parsing FSQ in my gmaps thing
_BPATH = '/L/backups/4sq'

def get_logger():
    import logging
    return logging.getLogger("fsq-provider")

class Checkin:
    def __init__(self, j) -> None:
        self.j = j

    @property
    def summary(self) -> str:
        return "checked into " + safe_get(self.j, 'venue', 'name', default="NO_NAME") + " " + self.j.get('shout', "") # TODO should should be bold...
    # TODO maybe return htmlish? if not html, interpret as string

    @property
    def dt(self) -> datetime:
        created = self.j['createdAt']  # this is local time
        offset = self.j['timeZoneOffset']
        tz = timezone(timedelta(minutes=offset))
        # a bit meh, but seems to work..
        # TODO localize??
        return datetime.fromtimestamp(created, tz=tz)

def get_raw(fname=None):
    if fname is None:
        fname = get_last_file(_BPATH, '.json')
    j = load_json_file(fname)

    assert isinstance(j, list)
    for chunk in j:
        del chunk['meta']
        del chunk['notifications']
    assert chunk.keys() == {'response'}
    assert chunk['response'].keys() == {'checkins'}

    return flatten([x['response']['checkins']['items'] for x in j])


# TODO not sure how to make it generic..
def get_checkins(*args, **kwargs):
    everything = get_raw(*args, **kwargs)
    checkins = sorted([Checkin(i) for i in everything], key=lambda c: c.dt)
    return checkins


# def extract(j):
#     assert isinstance(j, list)
#     for chunk in j:

class JsonComparer:
    def __init__(self, ignored=None):
        import re
        self.ignored = {} if ignored is None else {
            re.compile(i) for i in ignored
        }
        self.logger = get_logger()

    # TODO ugh, maybe just check if it dominates? and comparison if both dominate each other...
    def compare(self, a, b, path: str=""):
        # TODO not so sure about contains...
        if any(i.match(path) for i in self.ignored):
            self.logger.debug(f"ignoring path {path}")
            return True
        if a == b:
            return True
        alleq = True
        if isinstance(a, (int, float, bool, type(None), str)):
            self.logger.warning(f"at path {path}: {a} != {b}")
            alleq = False
        elif isinstance(a, list) or isinstance(b, list):
            if a is None or b is None or len(a) != len(b):
                alleq = False
            else:
                for i in range(len(a)):
                    if not self.compare(a[i], b[i], path + f"[]"):
                        self.logger.warning(f"at path {path}")
                        alleq = False
        elif isinstance(a, dict) or isinstance(b, dict):
            ka = set(a.keys())
            kb = set(b.keys())
            if ka != kb:
                import ipdb; ipdb.set_trace() 
                self.logger.warning(f"at path {path}")
                alleq = False
            else:
                for k in ka:
                    if not self.compare(a[k], b[k], path + f".{k}"):
                        alleq = False
        else:
            raise RuntimeError(f"Type mismatch: {type(a)} vs {type(b)}")

        return alleq


# TODO ok, so it's stats changing... I guess I can handle it same way I handle reddit...
def get_comparer():
    def chregex(rest: str):
        return r"^.\w+" + rest
    c = JsonComparer(ignored={
        chregex('.venue.stats'),
        chregex('.venue.menu.url'),

        # not so sure about these, but I guess makes sense. maybe add a sanity check that they are not too different??
        chregex('.venue.location.lat'),
        chregex('.venue.location.lng'),
        chregex('.venue.location.labeledLatLngs'),

        # TODO isMayor?
    })
    return c

# TODO right, I should only compare equivalent entries...
from kython import JSONType
def check_backups(backups: List[Tuple[JSONType, str]]):
    logger = get_logger()
    if len(backups) < 1:
        logger.info(f"Nothing to check: only {len(backups)} left")
        return []
    lastj, lastf = backups[-1]
    tocleanup: List[str] = []
    comp = get_comparer()
    for prevj, prevf in backups[-2::-1]:
        logger.info(f"Comparing {lastf} vs {prevf}")
        cres = comp.compare(prevj, lastj)
        if cres:
            logger.info(f"Removing {prevf}")
        else:
            logger.info(f"{lastf} differs from {prevf}")


def get_cid_map(bfile: str):
    raw = get_raw(bfile)
    return {i['id']: i for i in raw}


def cleanup_backups():
    from kython.data import get_all_files
    from pprint import pprint
    prev = None

    # ok, so. pick last
    # compare against prev. if there are no differences, delete prev. otherwise, choose prev as last. repeat

    bfiles = get_all_files(_BPATH, 'checkins_2018-08')
    backups = [(get_cid_map(bfile), bfile) for bfile in bfiles]
    for (pv, _), (nx, _) in zip(backups, backups[1:]):
        torm = set()
        for cid in nx:
            if cid not in pv:
                torm.add(cid)
        for cid in torm:
            del nx[cid] # meh?
    check_backups(backups)
    return

    for f in bfiles:
        print(f"Processing {f}")
        cur = {ch['id']: ch for ch in get_raw(f)}
        count = 0
        if prev is not None:
            for cid, c in cur.items():
                if cid not in prev:
                    print(f"new checkin {cid}!")
                else:
                    pc = prev[cid]
                    if pc != c:
                        compare_jsons(pc, c)
                        # import ipdb; ipdb.set_trace()
                        # print("WTF")
                        # pprint(pc)
                        # pprint(c)
                        # print("-----------")
                # pres = c in prev
                # if not pres:
                #     count += 1
            print(f"Difference: {count}")
        prev = cur
