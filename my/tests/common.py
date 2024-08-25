import os
from pathlib import Path
import re
import sys

import pytest

V = 'HPI_TESTS_KARLICOSS'

skip_if_not_karlicoss = pytest.mark.skipif(
    V not in os.environ,
    reason=f'test only works on @karlicoss data for now. Set env variable {V}=true to override.',
)


def reset_modules() -> None:
    '''
    A hack to 'unload' HPI modules, otherwise some modules might cache the config
    TODO: a bit crap, need a better way..
    '''
    to_unload = [m for m in sys.modules if re.match(r'my[.]?', m)]
    for m in to_unload:
        if 'my.pdfs' in m:
            # temporary hack -- since my.pdfs migrated to a 'lazy' config, this isn't necessary anymore
            # but if we reset module anyway, it confuses the ProcessPool inside my.pdfs
            continue
        del sys.modules[m]


def testdata() -> Path:
    d = Path(__file__).absolute().parent.parent.parent / 'testdata'
    assert d.exists(), d
    return d


# prevent pytest from treating this as test
testdata.__test__ = False  # type: ignore[attr-defined]
