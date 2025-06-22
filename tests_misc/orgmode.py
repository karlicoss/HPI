from my.tests.common import skip_if_not_karlicoss as pytestmark  # noqa: F401  # isort: skip


def test() -> None:
    from my import orgmode
    # FIXME why it's not used? Did I intend to test?
    # from my.core.orgmode import collect  # noqa: F401

    # meh
    results = list(orgmode.query().collect_all(lambda n: [n] if 'python' in n.tags else []))
    assert len(results) > 5
