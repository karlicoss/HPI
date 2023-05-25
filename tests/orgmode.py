from my.tests.common import skip_if_not_karlicoss as pytestmark

from my import orgmode
from my.core.orgmode import collect


def test() -> None:
    # meh
    results = list(orgmode.query().collect_all(lambda n: [n] if 'python' in n.tags else []))
    assert len(results) > 5
