from .common import assert_subpackage; assert_subpackage(__name__)

from .common import PathIsh
from .sqlite import sqlite_connect_immutable


# TODO wonder if also need to open without WAL.. test this on read-only directory/db file
def connect_readonly(db: PathIsh):
    import dataset # type: ignore
    # see https://github.com/pudo/dataset/issues/136#issuecomment-128693122
    # todo not sure if mode=ro has any benefit, but it doesn't work on read-only filesystems
    # maybe it should autodetect readonly filesystems and apply this? not sure
    creator = lambda: sqlite_connect_immutable(db)
    return dataset.connect('sqlite:///', engine_kwargs={'creator': creator})
