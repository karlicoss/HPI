from my.tests.common import skip_if_not_karlicoss as pytestmark  # isort: skip


def test() -> None:
    from my.rtm import all_tasks
    tasks = all_tasks()
    assert len([t for t in tasks if 'gluons' in t.title]) > 0
