from my import orgmode


def test() -> None:
    # meh
    results = list(orgmode.query().query_all(lambda x: x.with_tag('python')))
    assert len(results) > 5
