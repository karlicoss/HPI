from ..common import PathIsh
from ..sqlite import sqlite_connect_immutable


def connect_readonly(db: PathIsh):
    import dataset  # type: ignore[import-not-found]

    # see https://github.com/pudo/dataset/issues/136#issuecomment-128693122
    # todo not sure if mode=ro has any benefit, but it doesn't work on read-only filesystems
    # maybe it should autodetect readonly filesystems and apply this? not sure
    creator = lambda: sqlite_connect_immutable(db)
    return dataset.connect('sqlite:///', engine_kwargs={'creator': creator})
