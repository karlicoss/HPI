from my.emfit import get_datas


def test():
    datas = get_datas()
    for d in datas:
        assert d.start.tzinfo is not None
        assert d.end.tzinfo is not None
        assert d.sleep_start.tzinfo is not None
        assert d.sleep_end.tzinfo is not None


def test_tz():
    datas = get_datas()

    # this was winter time, so GMT, UTC+0
    [s0109] = [s for s in datas if s.date.strftime('%Y%m%d') == '20190109']
    assert s0109.end.strftime('%H:%M') == '06:42'

    # TODO FIXME ugh, it's broken?...
    # summer time, so UTC+1
    [s0411] = [s for s in datas if s.date.strftime('%Y%m%d') == '20190411']
    assert s0411.end.strftime('%H:%M') == '09:30'
