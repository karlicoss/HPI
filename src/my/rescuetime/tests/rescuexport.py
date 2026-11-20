import pytest

import my.rescuetime.rescuexport as provider
from my.core import __NOT_HPI_MODULE__  # noqa: F401


@pytest.mark.filterwarnings('error:The flat RescueTime config is deprecated')
def test_fake_data_reads_its_own_export() -> None:
    """The demo supplies a nested config and reads the entries it generated."""
    with provider.fake_data(rows=1):
        [entry] = provider.entries()
    assert isinstance(entry, provider.Entry)
