from pathlib import Path
import lzma
import sys
import zipfile

from ..kompress import kopen, kexists, CPath, ZipPath

import pytest


structure_data: Path = Path(__file__).parent / "structure_data"


def test_kopen(tmp_path: Path) -> None:
    "Plaintext handled transparently"
    # fmt: off
    assert kopen(tmp_path / 'file'   ).read() == 'just plaintext'
    assert kopen(tmp_path / 'file.xz').read() == 'compressed text'
    # fmt: on

    "For zips behaviour is a bit different (not sure about all this, tbh...)"
    assert kopen(tmp_path / 'file.zip', 'path/in/archive').read() == 'data in zip'


def test_kexists(tmp_path: Path) -> None:
    # TODO also test top level?
    # fmt: off
    assert     kexists(str(tmp_path / 'file.zip'), 'path/in/archive')
    assert not kexists(str(tmp_path / 'file.zip'), 'path/notin/archive')
    # fmt: on

    # TODO not sure about this?
    assert not kexists(tmp_path / 'nosuchzip.zip', 'path/in/archive')


def test_cpath(tmp_path: Path) -> None:
    # fmt: off
    CPath(str(tmp_path / 'file'  )).read_text() == 'just plaintext'
    CPath(    tmp_path / 'file.xz').read_text() == 'compressed text'
    # fmt: on


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


def test_zippath() -> None:
    target = structure_data / 'gdpr_export.zip'
    assert target.exists(), target  # precondition

    zp = ZipPath(target)

    # magic! convenient to make third party libraries agnostic of ZipPath
    assert isinstance(zp, Path)
    assert isinstance(zp, ZipPath)
    assert isinstance(zp / 'subpath', Path)
    # TODO maybe change __str__/__repr__? since it's a bit misleading:
    # Path('/code/hpi/tests/core/structure_data/gdpr_export.zip', 'gdpr_export/')

    assert ZipPath(target) == ZipPath(target)
    assert zp.absolute() == zp

    # shouldn't crash
    hash(zp)

    assert zp.exists()
    assert (zp / 'gdpr_export' / 'comments').exists()
    # check str constructor just in case
    assert (ZipPath(str(target)) / 'gdpr_export' / 'comments').exists()
    assert not (ZipPath(str(target)) / 'whatever').exists()

    matched = list(zp.rglob('*'))
    assert len(matched) > 0
    assert all(p.filepath == target for p in matched), matched

    rpaths = [p.relative_to(zp) for p in matched]
    gdpr_export = Path('gdpr_export')
    # fmt: off
    assert rpaths == [
        gdpr_export,
        gdpr_export / 'comments',
        gdpr_export / 'comments' / 'comments.json',
        gdpr_export / 'profile',
        gdpr_export / 'profile' / 'settings.json',
        gdpr_export / 'messages',
        gdpr_export / 'messages' / 'index.csv',
    ], rpaths
    # fmt: on

    # TODO hmm this doesn't work atm, whereas Path does
    # not sure if it should be defensive or something...
    # ZipPath('doesnotexist')
    # same for this one
    # assert ZipPath(Path('test'), 'whatever').absolute() == ZipPath(Path('test').absolute(), 'whatever')

    assert (ZipPath(target) / 'gdpr_export' / 'comments').exists()

    jsons = [p.relative_to(zp / 'gdpr_export') for p in zp.rglob('*.json')]
    # fmt: off
    assert jsons == [
        Path('comments', 'comments.json'),
        Path('profile' , 'settings.json'),
    ]
    # fmt: on

    # NOTE: hmm interesting, seems that ZipPath is happy with forward slash regardless OS?
    assert list(zp.rglob('mes*')) == [ZipPath(target, 'gdpr_export/messages')]

    iterdir_res = list((zp / 'gdpr_export').iterdir())
    assert len(iterdir_res) == 3
    assert all(isinstance(p, Path) for p in iterdir_res)

    # date recorded in the zip archive
    assert (zp / 'gdpr_export' / 'comments' / 'comments.json').stat().st_mtime > 1625000000
    # TODO ugh.
    # unzip -l shows the date  as 2021-07-01 09:43
    # however, python reads it as 2021-07-01 01:43 ??
    # don't really feel like dealing with this for now, it's not tz aware anyway
