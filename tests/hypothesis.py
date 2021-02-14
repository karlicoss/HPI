from .common import skip_if_not_karlicoss as pytestmark

def test() -> None:
    from my.hypothesis import pages, highlights
    assert len(list(pages())) > 10
    assert len(list(highlights())) > 10
