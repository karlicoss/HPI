import my.notes.orgmode as orgmode


def test():
    # meh
    results = orgmode.query().query_all(lambda x: x.with_tag('python'))
    assert len(results) > 5
