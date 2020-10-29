from pathlib import Path
from subprocess import check_call
import gzip
import lzma
import io
import zipfile

from my.core.kompress import kopen, kexists, CPath

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


from typing import Iterable, List
import warnings
from my.core import warn_if_empty
def test_warn_if_empty() -> None:
    @warn_if_empty
    def nonempty() -> Iterable[str]:
        yield 'a'
        yield 'aba'

    @warn_if_empty
    def empty() -> List[int]:
        return []

    # should be rejected by mypy!
    # todo how to actually test it?
    # @warn_if_empty
    # def baad() -> float:
    #     return 0.00

    # reveal_type(nonempty)
    # reveal_type(empty)

    with warnings.catch_warnings(record=True) as w:
        assert list(nonempty()) == ['a', 'aba']
        assert len(w) == 0

        eee = empty()
        assert eee == []
        assert len(w) == 1


def test_warn_iterable() -> None:
    from my.core.common import _warn_iterable
    i1: List[str] = ['a', 'b']
    i2: Iterable[int] = iter([1, 2, 3])
    # reveal_type(i1)
    # reveal_type(i2)
    x1 = _warn_iterable(i1)
    x2 = _warn_iterable(i2)
    # vvvv this should be flagged by mypy
    # _warn_iterable(123)
    # reveal_type(x1)
    # reveal_type(x2)
    with warnings.catch_warnings(record=True) as w:
        assert x1 is i1 # should be unchanged!
        assert len(w) == 0

        assert list(x2) == [1, 2, 3]
        assert len(w) == 0
