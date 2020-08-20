import typing

if typing.TYPE_CHECKING:
    from typing import Any
    # todo would be nice to use some real stubs..
    DataFrameT = Any
else:
    import pandas # type: ignore
    DataFrameT = pandas.DataFrame
