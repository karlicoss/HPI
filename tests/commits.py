from more_itertools import ilen
from my.coding.commits import commits


def test():
    all_commits = commits()
    assert ilen(all_commits) > 10
