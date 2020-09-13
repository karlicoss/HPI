'''
My exercise data, arbitrated between differen sources (mainly, Endomondo and various manual plaintext notes)

This is probably too specific to my needs, so later I will move it away to a personal 'layer'.
For now it's worth keeping it here as an example and perhaps utility functions might be useful for other HPI modules.
'''

from datetime import datetime, timedelta

from my.config import exercise as config


# todo predataframe?? entries??
def cross_trainer_data():
    # FIXME manual entries

    from porg import Org
    # TODO FIXME should use all org notes and just query from them?
    wlog = Org.from_file(config.workout_log)
    cross_table = wlog.xpath('//org[heading="Cross training"]//table')
    return cross_table.lines
    # todo hmm, converting an org table directly to pandas kinda makes sense?
    # could have a '.dataframe' method in orgparse, optional dependency


import pytz
# FIXME how to attach it properly?
tz = pytz.timezone('Europe/London')

def cross_trainer_manual_dataframe():
    '''
    Only manual org-mode entries
    '''
    import pandas as pd
    df = pd.DataFrame(cross_trainer_data())

    from ..core.orgmode import parse_org_datetime
    df['date'] = df['date'].apply(parse_org_datetime)

    def tzify(d: datetime) -> datetime:
        assert d.tzinfo is None, d
        return tz.localize(d)

    df['date'] = df['date'].apply(tzify)

    # TODO convert duration as well
    #
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
    grouped = edf.set_index('start_time').groupby(lambda t: t.date())
    singles = []
    for day, grp in grouped:
        if len(grp) != 1:
            # FIXME yield runtimeerror
            continue
        singles.append(grp)
    edf = pd.concat(singles)
    edf = edf.reset_index()

    mdf = cross_trainer_manual_dataframe()
    # now for each manual entry, find a 'close enough' endomondo entry
    rows = []
    idxs = []
    for i, row in mdf.iterrows():
        # todo rename 'date'??
        mdate = row['date']
        close = edf[edf['start_time'].apply(lambda t: pd_date_diff(t, mdate)).abs() < timedelta(hours=3)]
        if len(close) == 0:
            # FIXME emit warning -- nothing matched
            continue
        if len(close) > 1:
            # FIXME emit warning
            continue
        loc = close.index[0]
        # FIXME check and make defensive
        # assert loc not in idxs, (loc, row)
        idxs.append(loc)
        rows.append(row)
    mdf = pd.DataFrame(rows, index=idxs)

    df = edf.join(mdf, rsuffix='_manual')
    # TODO arbitrate kcal, duration, avg hr
    # compare power and hr?
    return df


def stats():
    from ..core import stat
    return stat(cross_trainer_data())


def pd_date_diff(a, b) -> timedelta:
    # ugh. pandas complains when we subtract timestamps in different timezones
    assert a.tzinfo is not None, a
    assert b.tzinfo is not None, b
    return a.to_pydatetime() - b.to_pydatetime()
