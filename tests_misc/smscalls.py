from my.tests.common import skip_if_not_karlicoss as pytestmark  # isort: skip

# TODO maybe instead detect if it has any data at all
# if none, then skip the test, say that user doesn't have any data?

# TODO implement via stat?
def test() -> None:
    from my.smscalls import calls, messages, mms
    assert len(list(calls())) > 10
    assert len(list(messages())) > 10
    assert len(list(mms())) > 10
