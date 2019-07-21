from my.ext.kobuddy import *

def get_todos():
    def with_todo(ann):
        if ann is None:
            ann = ''
        return 'todo' in ann.lower().split()
    return by_annotation(with_todo)


def test_todos():
    todos = get_todos()
    assert len(todos) > 3
