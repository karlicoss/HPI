"""
Various helpers for compression
"""
import pathlib
from pathlib import Path
from typing import Union

PathIsh = Union[Path, str]


def _zstd_open(path: Path):
    import zstandard as zstd # type: ignore
    fh = path.open('rb')
    dctx = zstd.ZstdDecompressor()
    reader = dctx.stream_reader(fh)
    return reader


def kopen(path: PathIsh, *args, **kwargs): # TODO is it bytes stream??
    pp = Path(path)
    suf = pp.suffix
    if suf in {'.xz'}:
        import lzma
        return lzma.open(pp, *args, **kwargs)
    elif suf in {'.zip'}:
        from zipfile import ZipFile
        return ZipFile(pp).open(*args, **kwargs)
    elif suf in {'.lz4'}:
        import lz4.frame # type: ignore
        return lz4.frame.open(str(pp))
    elif suf in {'.zstd'}:
        return _zstd_open(pp)
    else:
        kwargs['encoding'] = 'utf-8'
        return pp.open(*args, **kwargs)


import typing
import os

if typing.TYPE_CHECKING:
    # otherwise mypy can't figure out that BasePath is a type alias..
    BasePath = pathlib.Path
else:
    BasePath = pathlib.WindowsPath if os.name == 'nt' else pathlib.PosixPath


class CPath(BasePath):
    """
    Hacky way to support compressed files.
    If you can think of a better way to do this, please let me know! https://github.com/karlicoss/HPI/issues/20

    Ugh. So, can't override Path because of some _flavour thing.
    Path only has _accessor and _closed slots, so can't directly set .open method
    _accessor.open has to return file descriptor, doesn't work for compressed stuff.
    """
    def open(self, *args, **kwargs):
        # TODO assert read only?
        return kopen(str(self))


open = kopen # TODO remove?


# meh
def kexists(path: PathIsh, subpath: str) -> bool:
    try:
        kopen(path, subpath)
        return True
    except Exception:
        return False
