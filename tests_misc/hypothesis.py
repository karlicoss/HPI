from my.tests.common import skip_if_not_karlicoss as pytestmark  # noqa: F401  # isort: skip


def test() -> None:
    from my.hypothesis import highlights, pages
    assert len(list(pages())) > 10
    assert len(list(highlights())) > 10
