import os
from pathlib import Path

import pytest

V = 'HPI_TESTS_KARLICOSS'

skip_if_not_karlicoss = pytest.mark.skipif(
    V not in os.environ,
    reason=f'test only works on @karlicoss data for now. Set env variable {V}=true to override.',
)


def hpi_repo_root() -> Path:
    root_dir = Path(__file__).absolute().parent.parent.parent.parent
    src_dir = root_dir / 'src'
    assert src_dir.exists(), src_dir
    return root_dir


def testdata() -> Path:
    d = hpi_repo_root() / 'testdata'
    assert d.exists(), d
    return d


# prevent pytest from treating this as test
testdata.__test__ = False  # type: ignore[attr-defined]
