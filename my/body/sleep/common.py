from ...core import stat, Stats
from ...core.pandas import DataFrameT, check_dataframe as cdf


class Combine:
    def __init__(self, modules) -> None:
        self.modules = modules

    @cdf
    def dataframe(self, with_temperature: bool=True) -> DataFrameT:
        import pandas as pd # type: ignore
        # todo include 'source'?
        df = pd.concat([m.dataframe() for m in self.modules])

        if with_temperature:
            from ... import bluemaestro as BM
            bdf = BM.dataframe()
            temp = bdf['temp']

            def calc_avg_temperature(row):
                start = row['sleep_start']
                end   = row['sleep_end']
                if pd.isna(start) or pd.isna(end):
                    return None

                between = (start <= temp.index) & (temp.index <= end)
                # on no temp data, returns nan, ok
                return temp[between].mean()

            df['avg_temp'] = df.apply(calc_avg_temperature, axis=1)
        return df

    def stats(self) -> Stats:
        return stat(self.dataframe)
