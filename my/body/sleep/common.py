from ...core import Stats, stat
from ...core.pandas import DataFrameT
from ...core.pandas import check_dataframe as cdf


class Combine:
    def __init__(self, modules) -> None:
        self.modules = modules

    @cdf
    def dataframe(self, *, with_temperature: bool=True) -> DataFrameT:
        import pandas as pd
        # todo include 'source'?
        df = pd.concat([m.dataframe() for m in self.modules])

        if with_temperature:
            from ... import bluemaestro as BM
            bdf = BM.dataframe()
            temp = bdf['temp']

            # sort index and drop nans, otherwise indexing with [start: end] gonna complain
            temp = pd.Series(
                temp.values,
                index=pd.to_datetime(temp.index, utc=True)
            ).sort_index()
            temp = temp.loc[temp.index.dropna()]

            def calc_avg_temperature(row):
                start = row['sleep_start']
                end   = row['sleep_end']
                if pd.isna(start) or pd.isna(end):
                    return None

                # on no temp data, returns nan, ok
                return temp[start: end].mean()

            df['avg_temp'] = df.apply(calc_avg_temperature, axis=1)
        return df

    def stats(self) -> Stats:
        return stat(self.dataframe)
