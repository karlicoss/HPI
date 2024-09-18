from .internal import assert_subpackage; assert_subpackage(__name__)

from . import warnings

# do this later -- for now need to transition modules to avoid using kompress directly (e.g. ZipPath)
# warnings.high('my.core.kompress is deprecated, please use "kompress" library directly. See https://github.com/karlicoss/kompress')

try:
    from kompress import *
except ModuleNotFoundError as e:
    if e.name == 'kompress':
        warnings.high('Please install kompress (pip3 install kompress). Falling onto vendorized kompress for now.')
        from ._deprecated.kompress import *  # type: ignore[assignment]
    else:
        raise e
