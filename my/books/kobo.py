from functools import lru_cache

from .. import paths

@lru_cache()
def kobuddy_module():
    from kython import import_from
    return import_from(paths.kobuddy.repo, 'kobuddy')

kobuddy = kobuddy_module()
from kobuddy import *

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
