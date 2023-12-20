print(f'[main] {__name__} hello')

from .common import merge

def tweets() -> list[str]:
    from . import gdpr
    return merge(gdpr)
