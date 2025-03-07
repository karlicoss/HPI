from __future__ import annotations

import json

from . import warnings
from .pytest import parametrize


def json_loads(data: bytes | str):
    """
    Tries loading with orjson if it's available, otherwise falls back to stdlib json.
    """
    try:
        import orjson
    except ModuleNotFoundError as e:
        if e.name != 'orjson':
            raise
        warnings.medium("orjson is not installed, falling back to stdlib json. Install orjson for better performance.")
        return json.loads(data)
    else:
        return orjson.loads(data)


@parametrize("data, description", [('{"key": "value"}', "str"), (b'{"key": "value"}', "bytes")])
def test_json_loads_stdlib(data: str | bytes, description: str) -> None:
    from unittest.mock import patch

    import pytest

    with patch.dict('sys.modules', {'orjson': None}):  # hide orjson if it's installed
        with pytest.warns(UserWarning, match="orjson is not installed"):
            result = json_loads(data)

    assert result == {"key": "value"}


@parametrize("data, description", [('{"key": "value"}', "str"), (b'{"key": "value"}', "bytes")])
def test_json_loads_orjson(data: str | bytes, description: str) -> None:
    import pytest

    try:
        import orjson
    except ModuleNotFoundError:
        pytest.fail("orjson is not installed")

    result = json_loads(data)

    assert result == {"key": "value"}
