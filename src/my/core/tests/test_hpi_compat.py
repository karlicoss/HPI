import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize('legacy_first', [True, False], ids=['legacy-first', 'provider-first'])
@pytest.mark.parametrize('overlay', [False, True], ids=['builtin', 'overlay'])
def test_jawbone_compatibility_import_order(tmp_path: Path, *, legacy_first: bool, overlay: bool) -> None:
    """Old imports must resolve to the same provider regardless of which path was imported first."""
    config = tmp_path / 'config' / 'my'
    config.mkdir(parents=True)
    (config / 'config.py').write_text(
        f'from pathlib import Path\nclass jawbone:\n    export_dir = Path({str(tmp_path)!r})\n'
    )
    (tmp_path / 'sleeps.json').write_text('[]')

    overlay_root = tmp_path / 'overlay'
    if overlay:
        package = overlay_root / 'my' / 'jawbone'
        package.mkdir(parents=True)
        (package / 'api.py').write_text('def load_sleeps():\n    return ["overlay"]\n')

    imports = ['import my.jawbone as legacy', 'import my.jawbone.api as provider']
    if not legacy_first:
        imports.reverse()
    code = '\n'.join(imports)
    expected = ['overlay'] if overlay else []
    code += f'''
assert legacy.load_sleeps is provider.load_sleeps
assert legacy.load_sleeps() == {expected!r}
'''
    script = tmp_path / 'check.py'
    script.write_text(code)
    env = {**os.environ, 'MY_CONFIG': str(config.parent)}
    if overlay:
        env['PYTHONPATH'] = os.pathsep.join([str(overlay_root), env.get('PYTHONPATH', '')])
    result = subprocess.run(
        [sys.executable, '-Walways', str(script)], env=env, capture_output=True, text=True, check=True
    )
    assert ('importing my.jawbone is DEPRECATED' in result.stderr) == legacy_first, result.stderr
    if legacy_first:
        assert 'Instead, import from my.jawbone.api' in result.stderr
