from . import get_all_commits

# TODO shit. why can't it just be in __init__.py??

def test():
    commits = get_all_commits()
    assert len(commits) > 10
