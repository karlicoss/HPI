from my_configuration import paths
from my_configuration.repos.kobuddy.src.kobuddy import *

set_databases(paths.kobuddy.export_dir)

def get_todos():
    def with_todo(ann):
        if ann is None:
            ann = ''
        return 'todo' in ann.lower().split()
    return by_annotation(with_todo)


def test_todos():
    todos = get_todos()
    assert len(todos) > 3
