from my.foursquare import get_checkins

def test_checkins():
    checkins = get_checkins()
    assert len(checkins) > 100
    assert any('Victoria Park' in c.summary for c in checkins)
    # TODO cid_map??
