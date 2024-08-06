import os

import pytest


V = 'HPI_TESTS_USES_OPTIONAL_DEPS'

# TODO use it for serialize tests that are using simplejson/orjson?
skip_if_uses_optional_deps = pytest.mark.skipif(
    V not in os.environ,
    reason=f'test only works when optional dependencies are installed. Set env variable {V}=true to override.',
)
