from pathlib import Path

# TODO wonder if also need to open without WAL.. test this on read-only directory/db file
def connect_readonly(db: Path):
    import dataset # type: ignore
    # see https://github.com/pudo/dataset/issues/136#issuecomment-128693122
    import sqlite3
    creator = lambda: sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    return dataset.connect('sqlite:///', engine_kwargs={'creator': creator})
