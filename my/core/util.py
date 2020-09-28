from pathlib import Path
from itertools import chain
import os
import re
import pkgutil
from typing import List, Iterable

# TODO reuse in readme/blog post
# borrowed from https://github.com/sanitizers/octomachinery/blob/24288774d6dcf977c5033ae11311dbff89394c89/tests/circular_imports_test.py#L22-L55
def _iter_all_importables(pkg):
    yield from chain.from_iterable(
        _discover_path_importables(Path(p), pkg.__name__)
        for p in pkg.__path__
    )


def _discover_path_importables(pkg_pth, pkg_name):
    """Yield all importables under a given path and package."""
    for dir_path, dirs, file_names in os.walk(pkg_pth):
        file_names.sort()
        # NOTE: sorting dirs in place is intended, it's the way you're supposed to do it with os.walk
        dirs.sort()

        pkg_dir_path = Path(dir_path)

        if pkg_dir_path.parts[-1] == '__pycache__':
            continue

        if all(Path(_).suffix != '.py' for _ in file_names):
            continue

        rel_pt = pkg_dir_path.relative_to(pkg_pth)
        pkg_pref = '.'.join((pkg_name, ) + rel_pt.parts)


        # TODO might need to make it defensive and yield Exception (otherwise hpi doctor might fail for no good reason)
        yield from (
            pkg_path
            for _, pkg_path, _ in pkgutil.walk_packages(
                (str(pkg_dir_path), ), prefix=f'{pkg_pref}.',
            )
        )


# TODO marking hpi modules or unmarking non-modules? not sure what's worse
def ignored(m: str):
    excluded = [
        'kython.*',
        'mycfg_stub',
        'common',
        'error',
        'cfg',
        'core.*',
        'config.*',
        'jawbone.plots',
        'emfit.plot',

        # todo think about these...
        # 'google.takeout.paths',
        'bluemaestro.check',
        'location.__main__',
        'photos.utils',
        'books',
        'coding',
        'media',
        'reading',
        '_rss',
        'twitter.common',
        'rss.common',
        'lastfm.fill_influxdb',
    ]
    exs = '|'.join(excluded)
    return re.match(f'^my.({exs})$', m)


def modules() -> Iterable[str]:
    import my as pkg # todo not sure?
    for x in _iter_all_importables(pkg):
        if not ignored(x):
            yield x


def get_modules() -> List[str]:
    return list(modules())
