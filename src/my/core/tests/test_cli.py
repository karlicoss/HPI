import os
import sys
from pathlib import Path
from subprocess import check_call, run

import pytest


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


@pytest.mark.parametrize(('config', 'expected_exit_code'), [('count = 1', 0), ('count =', 1)])
def test_config_check_exit_code(tmp_path: Path, config: str, expected_exit_code: int) -> None:
    config_dir = tmp_path / 'my' / 'config'
    config_dir.mkdir(parents=True)
    (config_dir / '__init__.py').write_text(config)

    result = run(
        [sys.executable, '-m', 'my.core', 'config', 'check'],
        cwd=tmp_path,
        env={**os.environ, 'MY_CONFIG': str(tmp_path), 'PYTHONUTF8': '1'},
        capture_output=True,
        encoding='utf-8',
        check=False,
    )
    assert result.returncode == expected_exit_code, result.stderr
