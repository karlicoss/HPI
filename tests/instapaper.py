from my.instapaper import pages


def test_pages():
    assert len(list(pages())) > 3
