"""
Utils specific to hpi core, shouldn't really be used by HPI modules
"""
from __future__ import annotations


def _is_editable(package_name: str) -> bool:
    import importlib.metadata

    dist = importlib.metadata.distribution(package_name)
    dist_files = dist.files or []
    for path in dist_files:
        if str(path).endswith('.pth'):
            return True
    return False


def warn_if_not_using_src_layout(path: list[str]) -> None:
    contains_src = any('/src/my/' in p for p in path)
    if contains_src:
        return

    # __package__ won't work because it's gonna be 'my' rather than 'hpi'
    # seems like it's quite annoying to get distribition name from within the package, so easier to hardcode..
    distribution_name = 'hpi'
    try:
        editable = _is_editable(distribution_name)
    except:
        # it would be annoying if this somehow fails during the very first HPI import...
        # so just make defensive
        return

    if not editable:
        # nothing to check
        return


    from . import warnings

    MSG = '''
    Seems that your HPI is installed as editable and uses flat layout ( my/ directory next to .git folder).
    This was the case in older HPI versions (pre-20250123), but now src-layout is recommended ( src/my/ directory next to .git folder).

    Reinstall your HPI as editable again via 'pip install --editable /path/to/hpi'.
    See https://github.com/karlicoss/HPI/issues/316 for more info.
    '''

    warnings.high(MSG)
