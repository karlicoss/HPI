from my.tests.common import skip_if_not_karlicoss as pytestmark # isort: skip

from datetime import date, time


# todo private test.. move away
def test_tz() -> None:
    from my.jawbone import sleeps_by_date  # type: ignore[attr-defined]
    sleeps = sleeps_by_date()
    for s in sleeps.values():
        assert s.sleep_start.tzinfo is not None
        assert s.sleep_end.tzinfo is not None

    for dd, exp in [
            (date(year=2015, month=8 , day=28), time(hour=7, minute=20)),
            (date(year=2015, month=9 , day=15), time(hour=6, minute=10)),
    ]:
        sleep = sleeps[dd]
        end = sleep.sleep_end

        assert end.time() == exp
        # TODO fuck. on 0909 I woke up at around 6 according to google timeline
        # but according to jawbone, it was on 0910?? eh. I guess it's just shitty tracking.
