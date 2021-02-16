import os
from pathlib import Path
from typing import TYPE_CHECKING

from my.core.compat import windows
from my.core.common import get_files

import pytest # type: ignore


 # hack to replace all /tmp with 'real' tmp dir
 # not ideal, but makes tests more concise
def _get_files(x, *args, **kwargs):
    import my.core.common as C
    def repl(x):
        if isinstance(x, str):
            return x.replace('/tmp', TMP)
        elif isinstance(x, Path):
            assert x.parts[:2] == (os.sep, 'tmp') # meh
            return Path(TMP) / Path(*x.parts[2:])
        else:
            # iterable?
            return [repl(i) for i in x]

    x = repl(x)
    res = C.get_files(x, *args, **kwargs)
    return tuple(Path(str(i).replace(TMP, '/tmp')) for i in res) # hack back for asserts..


if not TYPE_CHECKING:
    get_files = _get_files


def test_single_file() -> None:
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


    "if the path starts with ~, we expand it"
    if not windows: # windows dowsn't have bashrc.. ugh
        assert get_files('~/.bashrc') == (
            Path('~').expanduser() / '.bashrc',
        )


def test_multiple_files() -> None:
    '''
    If you pass a directory/multiple directories, it flattens the contents
    '''
    create('/tmp/hpi_test/dir1/')
    create('/tmp/hpi_test/dir1/zzz')
    create('/tmp/hpi_test/dir1/yyy')
    # create('/tmp/hpi_test/dir1/whatever/') # TODO not sure about this... should really allow extra dirs
    create('/tmp/hpi_test/dir2/')
    create('/tmp/hpi_test/dir2/mmm')
    create('/tmp/hpi_test/dir2/nnn')
    create('/tmp/hpi_test/dir3/')
    create('/tmp/hpi_test/dir3/ttt')

    assert get_files([
        Path('/tmp/hpi_test/dir3'), # it takes in Path as well as str
        '/tmp/hpi_test/dir1',
    ]) == (
        # the paths are always returned in sorted order (unless you pass sort=False)
        Path('/tmp/hpi_test/dir1/yyy'),
        Path('/tmp/hpi_test/dir1/zzz'),
        Path('/tmp/hpi_test/dir3/ttt'),
    )


def test_explicit_glob() -> None:
    '''
    You can pass a glob to restrict the extensions
    '''

    create('/tmp/hpi_test/file_3.zip')
    create('/tmp/hpi_test/file_2.zip')
    create('/tmp/hpi_test/ignoreme')
    create('/tmp/hpi_test/file.zip')

    # todo walrus operator would be great here...
    expected = (
        Path('/tmp/hpi_test/file_2.zip'),
        Path('/tmp/hpi_test/file_3.zip'),
    )
    assert get_files('/tmp/hpi_test', 'file_*.zip') == expected

    "named argument should work too"
    assert get_files('/tmp/hpi_test', glob='file_*.zip') == expected


def test_implicit_glob() -> None:
    '''
    Asterisc in the path results in globing too.
    '''
    # todo hopefully that makes sense? dunno why would anyone actually rely on asteriscs in names..
    # this is very convenient in configs, so people don't have to use some special types

    create('/tmp/hpi_test/123/')
    create('/tmp/hpi_test/123/dummy')
    create('/tmp/hpi_test/123/file.zip')
    create('/tmp/hpi_test/456/')
    create('/tmp/hpi_test/456/dummy')
    create('/tmp/hpi_test/456/file.zip')

    assert get_files(['/tmp/hpi_test/*/*.zip']) == (
        Path('/tmp/hpi_test/123/file.zip'),
        Path('/tmp/hpi_test/456/file.zip'),
    )


def test_no_files() -> None:
    '''
    Test for empty matches. They work, but should result in warning
    '''
    assert get_files('')         == ()

    # todo test these for warnings?
    assert get_files([])         == ()
    assert get_files('bad*glob') == ()


# TODO not sure if should uniquify if the filenames end up same?
# TODO not sure about the symlinks? and hidden files?

import tempfile
TMP = tempfile.gettempdir()
test_path = Path(TMP) / 'hpi_test'

def setup():
    teardown()
    test_path.mkdir()


def teardown():
    import shutil
    if test_path.is_dir():
        shutil.rmtree(test_path)


def create(f: str) -> None:
    # in test body easier to use /tmp regardless the OS...
    f = f.replace('/tmp', TMP)
    if f.endswith('/'):
        Path(f).mkdir()
    else:
        Path(f).touch()
