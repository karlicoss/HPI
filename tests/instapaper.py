from my.instapaper import get_todos


def test_get_todos():
    for t in get_todos():
        print(t)
