'''
This file should only run when simplejson is installed,
but orjson is not installed to check compatibility
'''

# none of these should fail

import json
import simplejson
import pytest

from my.core.serialize import dumps, _A

def test_simplejson_fallback() -> None:

    # should fail to import
    with pytest.raises(ModuleNotFoundError):
        import orjson

    # simplejson should serialize namedtuple properly
    res: str = dumps(_A(x=1, y=2.0))
    assert json.loads(res) == {"x": 1, "y": 2.0}

