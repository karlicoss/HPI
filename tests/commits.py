from my.coding.commits import get_all_commits


def test():
    commits = get_all_commits()
    assert len(commits) > 10
