import os
import shutil
import tempfile
import zipfile
import atexit

from typing import Sequence, Generator, List, Union, Tuple
from contextlib import contextmanager
from pathlib import Path

from .common import LazyLogger


logger = LazyLogger(__name__, level="info")


def _structure_exists(base_dir: Path, paths: Sequence[str], partial: bool = False) -> bool:
    """
    Helper function for match_structure to check if
    all subpaths exist at some base directory

    For example:

    dir1
    ├── index.json
    └── messages
        └── messages.csv

    _structure_exists(Path("dir1"), ["index.json", "messages/messages.csv"])
    """
    targets_exist = ((base_dir / f).exists() for f in paths)
    if partial:
        return any(targets_exist)
    else:
        return all(targets_exist)


ZIP_EXT = {".zip"}


@contextmanager
def match_structure(
    base: Path,
    expected: Union[str, Sequence[str]],
    *,
    partial: bool = False,
) -> Generator[Tuple[Path, ...], None, None]:
    """
    Given a 'base' directory or zipfile, recursively search for one or more paths that match the
    pattern described in 'expected'. That can be a single string, or a list
    of relative paths (as strings) you expect at the same directory.

    If 'partial' is True, it only requires that one of the items in
    expected be present, not all of them.

    This reduces the chances of the user misconfiguring gdpr exports, e.g.
    if they zipped the folders instead of the parent directory or vice-versa

    When this finds a matching directory structure, it stops searching in that subdirectory
    and continues onto other possible subdirectories which could match

    If base is a zipfile, this extracts the zipfile into a temporary directory
    (configured by core_config.config.get_tmp_dir), and then searches the extracted
    folder for matching structures

    This returns the top of every matching folder structure it finds

    As an example:

    export_dir
    ├── exp_2020
    │   ├── channel_data
    │   │   ├── data1
    │   │   └── data2
    │   ├── index.json
    │   ├── messages
    │   │   └── messages.csv
    │   └── profile
    │       └── settings.json
    └── exp_2021
        ├── channel_data
        │   ├── data1
        │   └── data2
        ├── index.json
        ├── messages
        │   └── messages.csv
        └── profile
            └── settings.json

    Giving the top directory as the base, and some expected relative path like:

    with match_structure(Path("export_dir"), expected=("messages/messages.csv", "index.json")) as results:
        # results in this block is (Path("export_dir/exp_2020"), Path("export_dir/exp_2021"))

    This doesn't require an exhaustive list of expected values, but its a good idea to supply
    a complete picture of the expected structure to avoid false-positives

    This does not recursively unzip zipfiles in the subdirectories,
    it only unzips into a temporary directory if 'base' is a zipfile

    A common pattern for using this might be to use get_files to get a list
    of zipfiles or top-level gdpr export directories, and use match_structure
    to search the resulting paths for a export structure you're expecting
    """
    from . import core_config as CC

    tdir = CC.config.get_tmp_dir()

    if isinstance(expected, str):
        expected = (expected,)

    is_zip: bool = base.suffix in ZIP_EXT

    searchdir: Path = base.absolute()
    try:
        # if the file given by the user is a zipfile, create a temporary
        # directory and extract the zipfile to that temporary directory
        #
        # this temporary directory is removed in the finally block
        if is_zip:
            # sanity check before we start creating directories/rm-tree'ing things
            assert base.exists(), f"zipfile at {base} doesn't exist"

            searchdir = Path(tempfile.mkdtemp(dir=tdir))

            zf = zipfile.ZipFile(base)
            zf.extractall(path=str(searchdir))

        else:
            if not searchdir.is_dir():
                raise NotADirectoryError(f"Expected either a zipfile or a directory, received {searchdir}")

        matches: List[Path] = []
        possible_targets: List[Path] = [searchdir]

        while len(possible_targets) > 0:
            p = possible_targets.pop(0)

            if _structure_exists(p, expected, partial=partial):
                matches.append(p)
            else:
                # extend the list of possible targets with any subdirectories
                for f in os.scandir(p):
                    if f.is_dir():
                        possible_targets.append(p / f.name)

        if len(matches) == 0:
            logger.warning(f"""While searching {base}, could not find a matching folder structure. Expected {expected}. You're probably missing required files in the gdpr/export""")

        yield tuple(matches)

    finally:

        if is_zip:
            # make sure we're not mistakenly deleting data
            assert str(searchdir).startswith(str(tdir)), f"Expected the temporary directory for extracting zip to start with the temporary directory prefix ({tdir}), found {searchdir}"

            shutil.rmtree(str(searchdir))


def warn_leftover_files() -> None:
    from . import core_config as CC

    base_tmp: Path = CC.config.get_tmp_dir()
    leftover: List[Path] = list(base_tmp.iterdir())
    if leftover:
        logger.debug(f"at exit warning: Found leftover files in temporary directory '{leftover}'. this may be because you have multiple hpi processes running -- if so this can be ignored")


atexit.register(warn_leftover_files)
