from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

V = 'HPI_TESTS_USES_OPTIONAL_DEPS'

# TODO use it for serialize tests that are using simplejson/orjson?
skip_if_uses_optional_deps = pytest.mark.skipif(
    V not in os.environ,
    reason=f'test only works when optional dependencies are installed. Set env variable {V}=true to override.',
)


# TODO maybe move to hpi core?
@contextmanager
def tmp_environ_set(key: str, value: str | None) -> Iterator[None]:
    prev_value = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if prev_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev_value
