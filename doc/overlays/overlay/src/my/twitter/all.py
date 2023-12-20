print(f'[overlay] {__name__} hello')

from .common import merge

def tweets() -> list[str]:
    from . import gdpr
    from . import talon
    return merge(gdpr, talon)
