import os
from pathlib import Path

import pytest

V = 'HPI_TESTS_KARLICOSS'

skip_if_not_karlicoss = pytest.mark.skipif(
    V not in os.environ,
    reason=f'test only works on @karlicoss data for now. Set env variable {V}=true to override.',
)


def testdata() -> Path:
    d = Path(__file__).absolute().parent.parent.parent / 'testdata'
    assert d.exists(), d
    return d


# prevent pytest from treating this as test
testdata.__test__ = False  # type: ignore[attr-defined]
