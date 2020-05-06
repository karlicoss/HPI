from pathlib import Path
from subprocess import check_call
import gzip
import lzma
import io
import zipfile

from my.kython.kompress import kopen, kexists, CPath

def test_kopen(tmp_path: Path) -> None:
    "Plaintext handled transparently"
    assert kopen(tmp_path / 'file'   ).read() == 'just plaintext'
    assert kopen(tmp_path / 'file.xz').read() == 'compressed text'

    "For zips behaviour is a bit different (not sure about all this, tbh...)"
    assert kopen(tmp_path / 'file.zip', 'path/in/archive').read() == 'data in zip'


def test_kexists(tmp_path: Path) -> None:
    assert     kexists(str(tmp_path / 'file.zip'), 'path/in/archive')
    assert not kexists(str(tmp_path / 'file.zip'), 'path/notin/archive')

    # TODO not sure about this?
    assert not kexists(tmp_path / 'nosuchzip.zip', 'path/in/archive')


def test_cpath(tmp_path: Path) -> None:
    CPath(str(tmp_path / 'file'  )).read_text() == 'just plaintext'
    CPath(    tmp_path / 'file.xz').read_text() == 'compressed text'
    # TODO not sure about zip files??


import pytest # type: ignore

@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    (tmp_path / 'file').write_text('just plaintext')
    with (tmp_path / 'file.xz').open('wb') as f:
        with lzma.open(f, 'w') as lzf:
            lzf.write(b'compressed text')
    with zipfile.ZipFile(tmp_path / 'file.zip', 'w') as zf:
        zf.writestr('path/in/archive', 'data in zip')
    try:
        yield None
    finally:
        pass


# meh
from my.core.error import test_sort_res_by
