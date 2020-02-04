# TODO how to make it mypy friendly? maybe defensive import? or mypy config? or interface file?

try:
    import mycfg
except ImportError:
    import warnings
    warnings.warn("mycfg package isn't found! That might result in issues")

    from . import fake_mycfg as mycfg # type: ignore[no-redef]
    import sys
    sys.modules['mycfg'] = mycfg
    del sys
