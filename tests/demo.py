from pathlib import Path
from more_itertools import ilen

# TODO NOTE: this wouldn't work because of an early my.config.demo import
# from my.demo import items

def test_dynamic_config(tmp_path: Path) -> None:
    import my.config

    class user_config:
        username  = 'user'
        data_path = f'{tmp_path}/*.json'
    my.config.demo = user_config # type: ignore[misc, assignment]

    from my.demo import items
    [item1, item2] = items()
    assert item1.username == 'user'


import pytest # type: ignore
@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    (tmp_path / 'data.json').write_text('''
[
    {"key1": 1},
    {"key2": 2}
]
''')
    yield
