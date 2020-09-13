'''
My exercise data, arbitrated between differen sources (mainly, Endomondo and various manual plaintext notes)

This is probably too specific to my needs, so later I will move it away to a personal 'layer'.
For now it's worth keeping it here as an example and perhaps utility functions might be useful for other HPI modules.
'''

from datetime import datetime, timedelta
from typing import Optional

from my.config import exercise as config


import pytz
# FIXME how to attach it properly?
tz = pytz.timezone('Europe/London')

def tzify(d: datetime) -> datetime:
    assert d.tzinfo is None, d
    return tz.localize(d)


# todo predataframe?? entries??
def cross_trainer_data():
    # FIXME some manual entries in python
    # I guess just convert them to org

    from porg import Org
    # FIXME should use all org notes and just query from them?
    wlog = Org.from_file(config.workout_log)
    cross_table = wlog.xpath('//org[heading="Cross training"]//table')

    def maybe(f):
        def parse(s):
            if len(s) == 0:
                return None
            return f(s)
        return parse

    def parse_mm_ss(x: str) -> timedelta:
        hs, ms = x.split(':')
        return timedelta(seconds=int(hs) * 60 + int(ms))

    # todo eh. not sure if there is a way of getting around writing code...
    # I guess would be nice to have a means of specifying type in the column? maybe multirow column names??
    # need to look up org-mode standard..
    from ..core.orgmode import parse_org_datetime
    mappers = {
        'duration': lambda s: parse_mm_ss(s),
        'date'    : lambda s: tzify(parse_org_datetime(s)),
    }
    for row in cross_table.lines:
        # todo make more defensive, fallback on nan for individual fields??
        try:
            d = {}
            for k, v in row.items():
                mapper = mappers.get(k, maybe(float))
                d[k] = mapper(v)
            yield d
        except Exception as e:
            # todo add parsing context
            yield {'error': str(e)}

    # todo hmm, converting an org table directly to pandas kinda makes sense?
    # could have a '.dataframe' method in orgparse, optional dependency


def cross_trainer_manual_dataframe():
    '''
    Only manual org-mode entries
    '''
    import pandas as pd
    df = pd.DataFrame(cross_trainer_data())
    return df


def cross_trainer_dataframe():
    '''
    Attaches manually logged data (which Endomondo can't capture) and attaches it to Endomondo
    '''
    import pandas as pd

    from ..endomondo import dataframe as EDF
    edf = EDF()
    edf = edf[edf['sport'].str.contains('Cross training')]


    # Normalise and assume single bout of exercise per day
    # TODO this could be useful for other providers..
    # todo hmm maybe this bit is not really that necessary for this function??
    # just let it fail further down
    grouped = edf.set_index('start_time').groupby(lambda t: t.date())
    singles = []
    for day, grp in grouped:
        if len(grp) != 1:
            # FIXME yield runtimeerror
            continue
        else:
            singles.append(grp)
    edf = pd.concat(singles)
    edf = edf.reset_index()

    mdf = cross_trainer_manual_dataframe()
    # now for each manual entry, find a 'close enough' endomondo entry
    rows = []
    idxs = []
    for i, row in mdf.iterrows():
        mdate = row['date']
        close = edf[edf['start_time'].apply(lambda t: pd_date_diff(t, mdate)).abs() < timedelta(hours=3)]
        idx: Optional[int]
        rd = row.to_dict()
        # todo in case of error, 'start date' becomes 'date'??
        if len(close) == 0:
            idx = None
            d = {
                **rd,
                'error': 'no endomondo matches',
            }
        elif len(close) > 1:
            idx = None
            d = {
                **rd,
                'error': 'multiple endomondo matches',
                # todo add info on which exactly??
            }
        else:
            idx = close.index[0]
            d = rd

            if idx in idxs:
                # todo might be a good idea to remove the original match as well?
                idx = None
                d = {
                    **rd,
                    'error': 'manual entry matched multiple times',
                }
        idxs.append(idx)
        rows.append(d)
    mdf = pd.DataFrame(rows, index=idxs)

    # todo careful about 'how'? we need it to preserve the errors
    # maybe pd.merge is better suited for this??
    df = edf.join(mdf, how='outer', rsuffix='_manual')
    # TODO arbitrate kcal, duration, avg hr
    # compare power and hr? add 'quality' function??
    return df


def stats():
    from ..core import stat
    return stat(cross_trainer_data())


def compare_manual():
    df = cross_trainer_dataframe()
    df = df.set_index('start_time')

    df = df[[
        'kcal'    , 'kcal_manual',
        'duration', 'duration_manual',
    ]].dropna()
    print(df.to_string())


def pd_date_diff(a, b) -> timedelta:
    # ugh. pandas complains when we subtract timestamps in different timezones
    assert a.tzinfo is not None, a
    assert b.tzinfo is not None, b
    return a.to_pydatetime() - b.to_pydatetime()
