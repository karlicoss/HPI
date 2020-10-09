from ...core import stat, Stats
from ...core.pandas import DataFrameT, check_dataframe as cdf


class Combine:
    def __init__(self, modules) -> None:
        self.modules = modules

    @cdf
    def dataframe(self) -> DataFrameT:
        import pandas as pd # type: ignore
        # todo include 'source'?
        df = pd.concat([m.dataframe() for m in self.modules])
        return df

    def stats(self) -> Stats:
        return stat(self.dataframe)
