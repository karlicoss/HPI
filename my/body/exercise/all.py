'''
Combined exercise data
'''
from ...core.pandas import DataFrameT, check_dataframe


@check_dataframe
def dataframe() -> DataFrameT:
    # this should be somehow more flexible...
    import pandas as pd

    from ...endomondo import dataframe as EDF
    from ...runnerup import dataframe as RDF
    return pd.concat([
        EDF(),
        RDF(),
    ])
