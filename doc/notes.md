Just some random notes which will be converted in proper documentation later.


# apsw for sqlite
apsw is a faster sqlite adapter, for now I experimented with it in my.bluemaestro module.
I've seen about 30% speedup from using it which seems promising.

Pros:
- interface wise (e.g. connection/cursor) seems compatible with sqlite?
- possible free threading support later? https://github.com/rogerbinns/apsw/issues/568

Some issues:
- not that popular (800 github stars)
- doesn't support osx. Also doesn't properly set tags, i.e. you can still install it. On CI it segfaulted and on my laptop just didn't import anything?
- mypy doesn't work on python <= 3.10?
- setup.py is a bit insane https://github.com/rogerbinns/apsw/blob/master/setup.py

