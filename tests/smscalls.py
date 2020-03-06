from my.smscalls import calls


# TODO that's a pretty dumb test; perhaps can be generic..
def test():
    assert len(list(calls())) > 10
