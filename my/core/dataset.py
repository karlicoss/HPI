from pathlib import Path

# TODO wonder if also need to open without WAL.. test this on read-only directory/db file
def connect_readonly(db: Path):
    import dataset # type: ignore
    # see https://github.com/pudo/dataset/issues/136#issuecomment-128693122
    # todo not sure if mode=ro has any benefit, but it doesn't work on read-only filesystems
    # maybe it should autodetect readonly filesystems and apply this? not sure
    import sqlite3
    # https://www.sqlite.org/draft/uri.html#uriimmutable
    creator = lambda: sqlite3.connect(f'file:{db}?immutable=1', uri=True)
    return dataset.connect('sqlite:///', engine_kwargs={'creator': creator})
