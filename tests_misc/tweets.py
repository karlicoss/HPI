from my.tests.common import skip_if_not_karlicoss as pytestmark  # isort: skip
# todo current test doesn't depend on data, in principle...
# should make lazy loading the default..


import json
from datetime import datetime, timezone


def test_tweet() -> None:
    from my.twitter.archive import Tweet
    raw = """
 {
  "retweeted" : false,
  "entities" : {
    "hashtags" : [ ],
    "symbols" : [ ],
    "user_mentions" : [ ],
    "urls" : [ {
      "url" : "https://t.co/vUg4W6nxwU",
      "expanded_url" : "https://intelligence.org/2013/12/13/aaronson/",
      "display_url" : "intelligence.org/2013/12/13/aar…",
      "indices" : [ "120", "143" ]
    }
    ]
  },
  "display_text_range" : [ "0", "90" ],
  "favorite_count" : "0",
  "in_reply_to_status_id_str" : "24123424",
  "id_str" : "2328934829084",
  "in_reply_to_user_id" : "23423424",
  "truncated" : false,
  "retweet_count" : "0",
  "id" : "23492349032940",
  "in_reply_to_status_id" : "23482984932084",
  "created_at" : "Thu Aug 30 07:12:48 +0000 2012",
  "favorited" : false,
  "full_text" : "this is a test tweet",
  "lang" : "ru",
  "in_reply_to_screen_name" : "whatever",
  "in_reply_to_user_id_str" : "3748274"
}
    """
    t = Tweet(json.loads(raw), screen_name='whatever')
    assert t.permalink is not None
    assert t.dt == datetime(year=2012, month=8, day=30, hour=7, minute=12, second=48, tzinfo=timezone.utc)
    assert t.text == 'this is a test tweet'
    assert t.tid  == '2328934829084'
    assert t.entities is not None
