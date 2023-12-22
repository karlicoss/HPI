import importhook

@importhook.on_import('my.twitter.gdpr')
def on_import(gdpr):
    print("EXECUTING IMPORT HOOK!")
    tweets_orig = gdpr.tweets
    def tweets_patched():
        return [t.replace('gdpr', 'GDPR') for t in tweets_orig()]
    gdpr.tweets = tweets_patched
