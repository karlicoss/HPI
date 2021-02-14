from .common import skip_if_not_karlicoss as pytestmark

from more_itertools import ilen

def test() -> None:
    from my.coding.commits import commits
    all_commits = commits()
    assert ilen(all_commits) > 10
