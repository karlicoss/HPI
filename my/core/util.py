from pathlib import Path
from itertools import chain
import os
import re
import pkgutil
from typing import List

# TODO reuse in readme/blog post
# borrowed from https://github.com/sanitizers/octomachinery/blob/24288774d6dcf977c5033ae11311dbff89394c89/tests/circular_imports_test.py#L22-L55
def _find_all_importables(pkg):
    """Find all importables in the project.
    Return them in order.
    """
    return sorted(
        set(
            chain.from_iterable(
                _discover_path_importables(Path(p), pkg.__name__)
                for p in pkg.__path__
            ),
        ),
    )


def _discover_path_importables(pkg_pth, pkg_name):
    """Yield all importables under a given path and package."""
    for dir_path, _d, file_names in os.walk(pkg_pth):
        pkg_dir_path = Path(dir_path)

        if pkg_dir_path.parts[-1] == '__pycache__':
            continue

        if all(Path(_).suffix != '.py' for _ in file_names):
            continue

        rel_pt = pkg_dir_path.relative_to(pkg_pth)
        pkg_pref = '.'.join((pkg_name, ) + rel_pt.parts)


        yield from (
            pkg_path
            for _, pkg_path, _ in pkgutil.walk_packages(
                (str(pkg_dir_path), ), prefix=f'{pkg_pref}.',
            )
        )


# todo need a better way to mark module as 'interface'
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


def get_modules() -> List[str]:
    import my as pkg # todo not sure?
    importables = _find_all_importables(pkg)
    public = [x for x in importables if not ignored(x)]
    return public
