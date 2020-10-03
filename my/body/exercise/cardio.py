'''
Cardio data, filtered from Endomondo and inferred from other data sources
'''
from ...core.pandas import DataFrameT, check_dataframe as cdf


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


@cdf
def endomondo_cardio() -> DataFrameT:
    assert len(CARDIO.intersection(NOT_CARDIO)) == 0, (CARDIO, NOT_CARDIO)

    from ...endomondo import dataframe as EDF
    df = EDF()

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


def dataframe() -> DataFrameT:
    return endomondo_cardio()
