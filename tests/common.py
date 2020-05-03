from pathlib import Path
from my.common import get_files

import pytest # type: ignore


def test_single_file():
    '''
    Regular file path is just returned as is.
    '''

    "Exception if it doesn't exist"
    with pytest.raises(Exception):
        get_files('/tmp/hpi_test/file.ext')


    create('/tmp/hpi_test/file.ext')

    '''
    Couple of things:
    1. Return type is a tuple, it's friendlier for hashing/caching
    2. It always return pathlib.Path instead of plain strings
    '''
    assert get_files('/tmp/hpi_test/file.ext') == (
        Path('/tmp/hpi_test/file.ext'),
    )




test_path = Path('/tmp/hpi_test')
def setup():
    teardown()
    test_path.mkdir()


def teardown():
    import shutil
    if test_path.is_dir():
        shutil.rmtree(test_path)


from my.common import PathIsh
def create(f: PathIsh) -> None:
    Path(f).touch()
