'''
My cross trainer exercise data, arbitrated from different sources (mainly, Endomondo and manual text notes)

This is probably too specific to my needs, so later I will move it away to a personal 'layer'.
For now it's worth keeping it here as an example and perhaps utility functions might be useful for other HPI modules.
'''

from __future__ import annotations

from datetime import datetime, timedelta

import pytz

from my.config import exercise as config

from ...core.orgmode import Table, TypedTable, collect, parse_org_datetime
from ...core.pandas import DataFrameT
from ...core.pandas import check_dataframe as cdf

# FIXME how to attach it properly?
tz = pytz.timezone('Europe/London')

def tzify(d: datetime) -> datetime:
    assert d.tzinfo is None, d
    return tz.localize(d)


# todo predataframe?? entries??
def cross_trainer_data():
    # FIXME some manual entries in python
    # I guess just convert them to org
    import orgparse
    # todo should use all org notes and just query from them?
    wlog = orgparse.load(config.workout_log)

    [table] = collect(
        wlog,
        lambda n: [] if n.heading != 'Cross training' else [x for x in n.body_rich if isinstance(x, Table)]
    )
    cross_table = TypedTable(table)

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
    mappers = {
        'duration': lambda s: parse_mm_ss(s),
        'date'    : lambda s: tzify(parse_org_datetime(s)),
        'comment' : str,
    }
    for row in cross_table.as_dicts:
        # todo make more defensive, fallback on nan for individual fields??
        try:
            d = {}
            for k, v in row.items():
                # todo have something smarter... e.g. allow pandas to infer the type??
                mapper = mappers.get(k, maybe(float))
                d[k] = mapper(v) # type: ignore[operator]
            yield d
        except Exception as e:
            # todo add parsing context
            yield {'error': str(e)}

    # todo hmm, converting an org table directly to pandas kinda makes sense?
    # could have a '.dataframe' method in orgparse, optional dependency


@cdf
def cross_trainer_manual_dataframe() -> DataFrameT:
    '''
    Only manual org-mode entries
    '''
    import pandas as pd
    df = pd.DataFrame(cross_trainer_data())
    return df

# this should be enough?..
_DELTA = timedelta(hours=10)

# todo check error handling by introducing typos (e.g. especially dates) in org-mode
@cdf
def dataframe() -> DataFrameT:
    '''
    Attaches manually logged data (which Endomondo can't capture) and attaches it to Endomondo
    '''
    import pandas as pd

    from ...endomondo import dataframe as EDF
    edf = EDF()
    edf = edf[edf['sport'].str.contains('Cross training')]

    mdf = cross_trainer_manual_dataframe()
    # TODO shit. need to always remember to split errors???
    # on the other hand, dfs are always untyped. so it's not too bad??
    # now for each manual entry, find a 'close enough' endomondo entry
    # ideally it's a 1-1 (or 0-1) relationship, but there might be errors
    rows = []
    idxs = [] # type: ignore[var-annotated]
    NO_ENDOMONDO = 'no endomondo matches'
    for _i, row in mdf.iterrows():
        rd = row.to_dict()
        mdate = row['date']
        if pd.isna(mdate):
            # todo error handling got to be easier. seriously, mypy friendly dataframes would be amazing
            idxs.append(None)
            rows.append(rd) # presumably has an error set
            continue

        idx: int | None
        close = edf[edf['start_time'].apply(lambda t: pd_date_diff(t, mdate)).abs() < _DELTA]
        if len(close) == 0:
            idx = None
            d = {
                **rd,
                'error': NO_ENDOMONDO,
            }
        elif len(close) > 1:
            idx = None
            d = {
                **rd,
                'error': f'one manual, many endomondo: {close}',
            }
        else:
            idx = close.index[0]
            d = rd

            if idx in idxs:
                # todo might be a good idea to remove the original match as well?
                idx = None
                d = {
                    **rd,
                    'error': 'one endomondo, many manual',
                }
        idxs.append(idx)
        rows.append(d)
    mdf = pd.DataFrame(rows, index=idxs)

    # todo careful about 'how'? we need it to preserve the errors
    # maybe pd.merge is better suited for this??
    df = edf.join(mdf, how='outer', rsuffix='_manual')
    # todo reindex? so we don't have Nan leftovers

    # todo set date anyway? maybe just squeeze into the index??
    noendo = df['error'] == NO_ENDOMONDO
    # meh. otherwise the column type ends up object
    tz = df[noendo]['start_time'].dtype.tz
    df.loc[noendo, 'start_time'    ] = df[noendo]['date'           ].dt.tz_convert(tz)
    df.loc[noendo, 'duration'      ] = df[noendo]['duration_manual']
    df.loc[noendo, 'heart_rate_avg'] = df[noendo]['hr_avg'         ]

    # todo set sport?? set source?
    return df
# TODO arbitrate kcal, duration, avg hr
# compare power and hr? add 'quality' function??
# TODO wtf?? where is speed coming from??


from ...core import Stats, stat


def stats() -> Stats:
    return stat(cross_trainer_data)


def compare_manual() -> None:
    df = dataframe()
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
