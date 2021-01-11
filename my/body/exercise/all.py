'''
Combined exercise data
'''
from ...core.pandas import DataFrameT, check_dataframe


@check_dataframe
def dataframe() -> DataFrameT:
    # this should be somehow more flexible...
    from ...endomondo import dataframe as EDF
    from ...runnerup  import dataframe as RDF

    import pandas as pd # type: ignore
    return pd.concat([
        EDF(),
        RDF(),
    ])
