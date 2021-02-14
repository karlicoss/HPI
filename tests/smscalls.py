from .common import skip_if_not_karlicoss as pytestmark
# TODO maybe instead detect if it has any data at all
# if none, then skip the test, say that user doesn't have any data?

# TODO implement via stat?
def test() -> None:
    from my.smscalls import calls, messages
    assert len(list(calls())) > 10
    assert len(list(messages())) > 10
