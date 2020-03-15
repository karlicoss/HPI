from my.rtm import all_tasks


def test():
    tasks = all_tasks()
    assert len([t for t in tasks if 'gluons' in t.title]) > 0
