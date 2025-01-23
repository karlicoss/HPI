from my.tests.common import skip_if_not_karlicoss as pytestmark


def test() -> None:
    from my.emfit import datas
    # TODO this should be implement via sanity checks/stat instead?
    # the same code will be used for tests & for user reports
    ds = [x for x in datas() if not isinstance(x, Exception)]
    for d in ds:
        assert d.start.tzinfo is not None
        assert d.end.tzinfo is not None
        assert d.sleep_start.tzinfo is not None
        assert d.sleep_end.tzinfo is not None


def test_tz() -> None:
    from my.emfit import datas
    # TODO check errors too?
    ds = [x for x in datas() if not isinstance(x, Exception)]

    # this was winter time, so GMT, UTC+0
    [s0109] = [s for s in ds if s.date.strftime('%Y%m%d') == '20190109']
    assert s0109.end.strftime('%H:%M') == '06:42'

    # summer time, so UTC+1
    [s0411] = [s for s in ds if s.date.strftime('%Y%m%d') == '20190411']
    assert s0411.end.strftime('%H:%M') == '09:30'
