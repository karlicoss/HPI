from .common import skip_if_not_karlicoss as pytestmark

from more_itertools import ilen
# todo test against stats? not sure.. maybe both

def test_gdpr() -> None:
    import my.github.gdpr as gdpr
    assert ilen(gdpr.events()) > 100


def test() -> None:
    from my.coding.github import get_events
    events = get_events()
    assert ilen(events) > 100
    for e in events:
        print(e)
