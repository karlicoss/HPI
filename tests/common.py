import os

import pytest

V = 'HPI_TESTS_KARLICOSS'

skip_if_not_karlicoss = pytest.mark.skipif(
    V not in os.environ, reason=f'test only works on @karlicoss data for now. Set evn variable {V}=true to override.',
)
