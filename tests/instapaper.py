from .common import skip_if_not_karlicoss as pytestmark

def test_pages() -> None:
    # TODO ugh. need lazy import to simplify testing?
    from my.instapaper import pages
    assert len(list(pages())) > 3
