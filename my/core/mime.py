"""
Utils for mime/filetype handling
"""

from .internal import assert_subpackage; assert_subpackage(__name__)

import functools

from .common import PathIsh


@functools.lru_cache(1)
def _magic():
    import magic  # type: ignore

    # TODO also has uncompess=True? could be useful
    return magic.Magic(mime=True)


# TODO could reuse in pdf module?
import mimetypes  # todo do I need init()?


# todo wtf? fastermime thinks it's mime is application/json even if the extension is xz??
# whereas magic detects correctly: application/x-zstd and application/x-xz
def fastermime(path: PathIsh) -> str:
    paths = str(path)
    # mimetypes is faster, so try it first
    (mime, _) = mimetypes.guess_type(paths)
    if mime is not None:
        return mime
    # magic is slower but handles more types
    # TODO Result type?; it's kinda racey, but perhaps better to let the caller decide?
    return _magic().from_file(paths)
