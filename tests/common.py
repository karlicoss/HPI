import os

import pytest

skip_if_not_karlicoss = pytest.mark.skipif(
    'HPI_TESTS_KARLICOSS' not in os.environ, reason='test only works on @karlicoss data for now',
)
