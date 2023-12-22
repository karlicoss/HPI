print(f'[overlay2] {__name__} hello')

from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

def hack_gdpr_module() -> None:
    from . import gdpr
    tweets_orig = gdpr.tweets
    def tweets_patched():
        return [t.replace('gdpr', 'GDPR') for t in tweets_orig()]
    gdpr.tweets = tweets_patched

hack_gdpr_module()
