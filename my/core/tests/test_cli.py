import os
import sys
from subprocess import check_call


def test_lists_modules() -> None:
    # hack PYTHONUTF8 for windows
    # see  https://github.com/karlicoss/promnesia/issues/274
    # https://memex.zulipchat.com/#narrow/stream/279600-promnesia/topic/indexing.3A.20utf8.28emoji.29.20filenames.20in.20Windows
    # necessary for this test cause emooji is causing trouble
    # TODO need to fix it properly
    env = {
        **os.environ,
        'PYTHONUTF8': '1',
    }
    check_call([sys.executable, '-m', 'my.core', 'modules'], env=env)
