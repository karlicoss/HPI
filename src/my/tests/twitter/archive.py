import json
from datetime import datetime, timezone

from my.twitter.archive import Tweet


def test_tweet() -> None:
    raw = r"""
{
    "edit_info" : {
      "initial" : {
        "editTweetIds" : [
          "1269253350735982592"
        ],
        "editableUntil" : "2020-06-06T14:02:35.059Z",
        "editsRemaining" : "5",
        "isEditEligible" : true
      }
    },
    "retweeted" : false,
    "source" : "<a href=\"https://mobile.twitter.com\" rel=\"nofollow\">Twitter Web App</a>",
    "entities" : {
      "hashtags" : [ ],
      "symbols" : [ ],
      "user_mentions" : [ ],
      "urls" : [
        {
          "url" : "https://t.co/cnUyc7zASn",
          "expanded_url" : "https://beepb00p.xyz/promnesia.html",
          "display_url" : "beepb00p.xyz/promnesia.html",
          "indices" : [
            "44",
            "67"
          ]
        }
      ]
    },
    "display_text_range" : [
      "0",
      "139"
    ],
    "favorite_count" : "16",
    "id_str" : "1269253350735982592",
    "truncated" : false,
    "retweet_count" : "2",
    "id" : "1269253350735982592",
    "possibly_sensitive" : false,
    "created_at" : "Sat Jun 06 13:02:35 +0000 2020",
    "favorited" : false,
    "full_text" : "Finally published the post about Promnesia: https://t.co/cnUyc7zASn\n\nA story of how our browser history is broken and my attempt to fix it!",
    "lang" : "en"
}
    """.strip()
    t = Tweet(json.loads(raw), screen_name='whatever')
    assert t.permalink == 'https://twitter.com/whatever/status/1269253350735982592'
    assert t.dt == datetime(2020, 6, 6, 13, 2, 35, tzinfo=timezone.utc)
    assert (
        t.text
        == 'Finally published the post about Promnesia: https://beepb00p.xyz/promnesia.html\n\nA story of how our browser history is broken and my attempt to fix it!'
    )
    assert t.tid == '1269253350735982592'
    assert t.entities is not None
