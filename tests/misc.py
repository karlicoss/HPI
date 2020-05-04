from pathlib import Path
from subprocess import check_call
import gzip
import lzma
import io

from my.kython.kompress import kopen


import pytest # type: ignore

@pytest.fixture
def prepare(tmp_path: Path):
    (tmp_path / 'file').write_text('just plaintext')
    with (tmp_path / 'file.xz').open('wb') as f:
        with lzma.open(f, 'w') as lzf:
            lzf.write(b'compressed text')
    try:
        yield None
    finally:
        pass


def test_kopen(prepare, tmp_path: Path) -> None:
    "Plaintext handled transparently"
    assert kopen(tmp_path / 'file'   ).read() == 'just plaintext'
    assert kopen(tmp_path / 'file.xz').read() == b'compressed text' # FIXME make this str


def test_kexists(tmp_path: Path) -> None:
    # TODO
    raise RuntimeError


def test_cpath():
    # TODO
    raise RuntimeError


# TODO FIXME these tests should def run on CI
# TODO get rid of all decode utf8?
