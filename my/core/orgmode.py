"""
Various helpers for reading org-mode data
"""
from datetime import datetime


def parse_org_datetime(s: str) -> datetime:
    s = s.strip('[]')
    for fmt, cl in [
            ("%Y-%m-%d %a %H:%M", datetime),
            ("%Y-%m-%d %H:%M"   , datetime),
            # todo not sure about these... fallback on 00:00?
            # ("%Y-%m-%d %a"      , date),
            # ("%Y-%m-%d"         , date),
    ]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    else:
        raise RuntimeError(f"Bad datetime string {s}")
