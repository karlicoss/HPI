import os
from pathlib import Path

import pytest

V = 'HPI_TESTS_KARLICOSS'

skip_if_not_karlicoss = pytest.mark.skipif(
    V not in os.environ, reason=f'test only works on @karlicoss data for now. Set evn variable {V}=true to override.',
)

def reset_modules() -> None:
    '''
    A hack to 'unload' HPI modules, otherwise some modules might cache the config
    TODO: a bit crap, need a better way..
    '''
    import sys
    import re
    to_unload = [m for m in sys.modules if re.match(r'my[.]?', m)]
    for m in to_unload:
        del sys.modules[m]


def testdata() -> Path:
    d = Path(__file__).absolute().parent.parent / 'testdata'
    assert d.exists(), d
    return d
