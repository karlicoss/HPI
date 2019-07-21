from my.books.kobo.kobuddy import *


def test_todos():
    todos = get_todos()
    assert len(todos) > 3
