# TODO move elsewhere?

# these tests would only make sense with some existing data? although some of them would work for everyone..
# not sure what's a good way of handling this..

from my.media.youtube import get_watched


def test():
    watched = get_watched()
    assert len(watched) > 1000
