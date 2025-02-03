import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from kompress import CPath, ZipPath

from ..common import get_files


# hack to replace all /tmp with 'real' tmp dir
# not ideal, but makes tests more concise
# TODO get rid of this, it's super confusing..
def _get_files(x, *args, **kwargs):
    from ..common import get_files as get_files_orig

    def repl(x):
        if isinstance(x, str):
            return x.replace('/tmp', TMP)
        elif isinstance(x, Path):
            assert x.parts[:2] == (os.sep, 'tmp')  # meh
            return Path(TMP) / Path(*x.parts[2:])
        else:
            # iterable?
            return [repl(i) for i in x]

    x = repl(x)
    res = get_files_orig(x, *args, **kwargs)
    return tuple(type(i)(str(i).replace(TMP, '/tmp')) for i in res)  # hack back for asserts..


get_files_orig = get_files
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
    assert get_files('/tmp/hpi_test/file.ext') == (Path('/tmp/hpi_test/file.ext'),)

    is_windows = os.name == 'nt'
    "if the path starts with ~, we expand it"
    if not is_windows:  # windows doesn't have bashrc.. ugh
        assert get_files('~/.bashrc') == (Path('~').expanduser() / '.bashrc',)


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

    # fmt: off
    assert get_files([
        Path('/tmp/hpi_test/dir3'), # it takes in Path as well as str
        '/tmp/hpi_test/dir1',
    ]) == (
        # the paths are always returned in sorted order (unless you pass sort=False)
        Path('/tmp/hpi_test/dir1/yyy'),
        Path('/tmp/hpi_test/dir1/zzz'),
        Path('/tmp/hpi_test/dir3/ttt'),
    )
    # fmt: on


def test_explicit_glob() -> None:
    '''
    You can pass a glob to restrict the extensions
    '''

    create('/tmp/hpi_test/file_3.gz')
    create('/tmp/hpi_test/file_2.gz')
    create('/tmp/hpi_test/ignoreme')
    create('/tmp/hpi_test/file.gz')

    # todo walrus operator would be great here...
    expected = (
        Path('/tmp/hpi_test/file_2.gz'),
        Path('/tmp/hpi_test/file_3.gz'),
    )
    assert get_files('/tmp/hpi_test', 'file_*.gz') == expected

    "named argument should work too"
    assert get_files('/tmp/hpi_test', glob='file_*.gz') == expected


def test_implicit_glob() -> None:
    '''
    Asterisc in the path results in globing too.
    '''
    # todo hopefully that makes sense? dunno why would anyone actually rely on asteriscs in names..
    # this is very convenient in configs, so people don't have to use some special types

    create('/tmp/hpi_test/123/')
    create('/tmp/hpi_test/123/dummy')
    create('/tmp/hpi_test/123/file.gz')
    create('/tmp/hpi_test/456/')
    create('/tmp/hpi_test/456/dummy')
    create('/tmp/hpi_test/456/file.gz')

    assert get_files(['/tmp/hpi_test/*/*.gz']) == (
        Path('/tmp/hpi_test/123/file.gz'),
        Path('/tmp/hpi_test/456/file.gz'),
    )


def test_no_files() -> None:
    '''
    Test for empty matches. They work, but should result in warning
    '''
    assert get_files('') == ()

    # todo test these for warnings?
    assert get_files([]) == ()
    assert get_files('bad*glob') == ()


def test_compressed(tmp_path: Path) -> None:
    file1 = tmp_path / 'file_1.zstd'
    file2 = tmp_path / 'file_2.zip'
    file3 = tmp_path / 'file_3.csv'

    file1.touch()
    with zipfile.ZipFile(file2, 'w') as zf:
        zf.writestr('path/in/archive', 'data in zip')
    file3.touch()

    results = get_files_orig(tmp_path)
    [res1, res2, res3] = results
    assert isinstance(res1, CPath)
    assert isinstance(res2, ZipPath)  # NOTE this didn't work on vendorized kompress, but it's fine, was never used?
    assert not isinstance(res3, CPath)

    results = get_files_orig(
        [CPath(file1), ZipPath(file2), file3],
        # sorting a mixture of ZipPath/Path was broken in old kompress
        # it almost never happened though (usually it's only a bunch of ZipPath, so not a huge issue)
        sort=False,
    )
    [res1, res2, res3] = results
    assert isinstance(res1, CPath)
    assert isinstance(res2, ZipPath)
    assert not isinstance(res3, CPath)


# TODO not sure if should uniquify if the filenames end up same?
# TODO not sure about the symlinks? and hidden files?

TMP = tempfile.gettempdir()
test_path = Path(TMP) / 'hpi_test'


@pytest.fixture(autouse=True)
def prepare():
    teardown()
    test_path.mkdir()
    try:
        yield
    finally:
        teardown()


def teardown() -> None:
    if test_path.is_dir():
        shutil.rmtree(test_path)


def create(f: str) -> None:
    # in test body easier to use /tmp regardless the OS...
    f = f.replace('/tmp', TMP)
    if f.endswith('/'):
        Path(f).mkdir()
    else:
        Path(f).touch()
