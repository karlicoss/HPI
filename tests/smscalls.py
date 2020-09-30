from my.smscalls import calls, messages


# TODO that's a pretty dumb test; perhaps can be generic..
def test():
    assert len(list(calls())) > 10
    assert len(list(messages())) > 10
