"""
Various helpers for compression
"""
import pathlib
from pathlib import Path
from typing import Union, IO
import io

PathIsh = Union[Path, str]


def _zstd_open(path: Path, *args, **kwargs) -> IO[str]:
    import zstandard as zstd # type: ignore
    fh = path.open('rb')
    dctx = zstd.ZstdDecompressor()
    reader = dctx.stream_reader(fh)
    return io.TextIOWrapper(reader, **kwargs) # meh


# TODO returns protocol that we can call 'read' against?
# TODO use the 'dependent type' trick?
def kopen(path: PathIsh, *args, mode: str='rt', **kwargs) -> IO[str]:
    # TODO handle mode in *rags?
    encoding = kwargs.get('encoding', 'utf8')
    kwargs['encoding'] = encoding

    pp = Path(path)
    suf = pp.suffix
    if suf in {'.xz'}:
        import lzma
        r = lzma.open(pp, mode, *args, **kwargs)
        # should only happen for binary mode?
        # file:///usr/share/doc/python3/html/library/lzma.html?highlight=lzma#lzma.open
        assert not isinstance(r, lzma.LZMAFile), r
        return r
    elif suf in {'.zip'}:
        # eh. this behaviour is a bit dodgy...
        from zipfile import ZipFile
        zfile = ZipFile(pp)

        [subpath] = args # meh?

        ## oh god... https://stackoverflow.com/a/5639960/706389
        ifile = zfile.open(subpath, mode='r')
        ifile.readable = lambda: True  # type: ignore
        ifile.writable = lambda: False # type: ignore
        ifile.seekable = lambda: False # type: ignore
        ifile.read1    = ifile.read    # type: ignore
        # TODO pass all kwargs here??
        # todo 'expected "BinaryIO"'??
        return io.TextIOWrapper(ifile, encoding=encoding) # type: ignore[arg-type]
    elif suf in {'.lz4'}:
        import lz4.frame # type: ignore
        return lz4.frame.open(str(pp), mode, *args, **kwargs)
    elif suf in {'.zstd'}:
        return _zstd_open(pp, mode, *args, **kwargs)
    else:
        return pp.open(mode, *args, **kwargs)


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


open = kopen # TODO deprecate


# meh
def kexists(path: PathIsh, subpath: str) -> bool:
    try:
        kopen(path, subpath)
        return True
    except Exception:
        return False
