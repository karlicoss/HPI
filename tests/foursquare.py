from .common import skip_if_not_karlicoss as pytestmark

def test_checkins() -> None:
    from my.foursquare import get_checkins
    # todo reuse stats?
    checkins = get_checkins()
    assert len(checkins) > 100
    assert any('Victoria Park' in c.summary for c in checkins)
    # TODO cid_map??
