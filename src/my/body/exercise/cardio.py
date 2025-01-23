'''
Cardio data, filtered from various data sources
'''
from ...core.pandas import DataFrameT, check_dataframe

CARDIO     = {
    'Running',
    'Running, treadmill',
    'Cross training',
    'Walking',
    'Skating',
    'Spinning',
    'Skiing',
    'Table tennis',
    'Rope jumping',
}
# todo if it has HR data, take it into the account??
NOT_CARDIO = {
    'Other',
}


@check_dataframe
def dataframe() -> DataFrameT:
    assert len(CARDIO.intersection(NOT_CARDIO)) == 0, (CARDIO, NOT_CARDIO)

    from .all import dataframe as DF
    df = DF()

    # not sure...
    # df = df[df['heart_rate_avg'].notna()]

    is_cardio  = df['sport'].isin(CARDIO)
    not_cardio = df['sport'].isin(NOT_CARDIO)
    neither    = ~is_cardio & ~not_cardio
    # if neither -- count, but warn? or show error?

    # todo error about the rest??
    # todo append errors?
    df.loc[neither, 'error'] = 'Unexpected exercise type, please mark as cardio or non-cardio'
    df = df[is_cardio | neither]

    return df
