from pathlib import Path
import lzma
import zipfile

from my.core.kompress import kopen, kexists, CPath

import pytest # type: ignore


structure_data: Path = Path(__file__).parent / "structure_data"


def test_kopen(tmp_path: Path) -> None:
    "Plaintext handled transparently"
    assert kopen(tmp_path / 'file'   ).read() == 'just plaintext'
    assert kopen(tmp_path / 'file.xz').read() == 'compressed text'

    "For zips behaviour is a bit different (not sure about all this, tbh...)"
    assert kopen(tmp_path / 'file.zip', 'path/in/archive').read() == 'data in zip'


# TODO here?
def test_kexists(tmp_path: Path) -> None:
    # TODO also test top level?
    assert     kexists(str(tmp_path / 'file.zip'), 'path/in/archive')
    assert not kexists(str(tmp_path / 'file.zip'), 'path/notin/archive')

    # TODO not sure about this?
    assert not kexists(tmp_path / 'nosuchzip.zip', 'path/in/archive')


def test_cpath(tmp_path: Path) -> None:
    CPath(str(tmp_path / 'file'  )).read_text() == 'just plaintext'
    CPath(    tmp_path / 'file.xz').read_text() == 'compressed text'
    # TODO not sure about zip files??


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
    from my.core.kompress import ZipPath
    target = structure_data / 'gdpr_export.zip'
    assert target.exists(), target  # precondition

    zp = ZipPath(target)

    # magic! convenient to make third party libraries agnostic of ZipPath
    assert isinstance(zp, Path)
    # FIXME maybe change str? since it's a bit misleading...
    # Path('/code/hpi/tests/core/structure_data/gdpr_export.zip', 'gdpr_export/')

    assert ZipPath(target) == ZipPath(target)
    assert zp.absolute() == zp

    assert zp.exists()
    assert (zp / 'gdpr_export/comments').exists()
    # check str constructor just in case
    assert (ZipPath(str(target)) / 'gdpr_export/comments').exists()

    matched = list(zp.rglob('*'))
    assert len(matched) > 0
    assert all(p.filename == str(target) for p in matched), matched

    rpaths = [str(p.relative_to(zp)) for p in matched]
    assert rpaths == [
        'gdpr_export',
        'gdpr_export/comments',
        'gdpr_export/comments/comments.json',
        'gdpr_export/profile',
        'gdpr_export/profile/settings.json',
        'gdpr_export/messages',
        'gdpr_export/messages/index.csv',
    ], rpaths


    # TODO hmm this doesn't work atm, although Path does
    # not sure if it should be defensive or something...
    # ZipPath('doesnotexist')
    # same for this one
    # assert ZipPath(Path('test'), 'whatever').absolute() == ZipPath(Path('test').absolute(), 'whatever')
    #
    # FIXME vvv this should really work...
    # assert (ZipPath(target) / 'gdpr_export/comments').exists()
    # assert ZipPath(target, 'gdpr_export/comments').exists()

    jsons = [str(p.relative_to(zp / 'gdpr_export')) for p in zp.rglob('*.json')]
    assert jsons == [
        'comments/comments.json',
        'profile/settings.json',
    ]

    # FIXME uhh.. this doesn't work? without slash probably should...
    # assert list(zp.rglob('mes*')) == [ZipPath(target, 'gdpr_export/messages')]
    assert list(zp.rglob('mes*')) == [ZipPath(target, 'gdpr_export/messages/')]
