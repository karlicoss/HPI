import inspect
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from textwrap import dedent

import pytest


def _run(
    tmp_path: Path,
    scenario: Callable[..., None],
    *,
    pythonpath: Sequence[Path] = (),
    source_file: bool = False,
    **parameters: str | bool,
) -> None:
    """Extract a lintable scenario and run it with a fresh Python import cache.

    Scenarios import their own dependencies and receive parameters explicitly.
    By default, -c leaves caller source unavailable to the legacy-import detector.
    """
    assert inspect.isfunction(scenario)
    config = tmp_path / 'config' / 'my'
    config.mkdir(parents=True)
    (config / 'config.py').write_text('')
    env = {**os.environ, 'MY_CONFIG': str(config.parent)}
    if len(pythonpath) > 0:
        env['PYTHONPATH'] = os.pathsep.join([*map(str, pythonpath), env.get('PYTHONPATH', '')])

    code = dedent(inspect.getsource(scenario)) + f'\n{scenario.__name__}(**{parameters!r})\n'
    if source_file:
        script = tmp_path / 'check.py'
        script.write_text(code)
        command = [sys.executable, str(script)]
    else:
        command = [sys.executable, '-c', code]
    subprocess.run(command, env=env, check=True)


@pytest.mark.parametrize('legacy_first', [True, False], ids=['legacy-first', 'provider-first'])
@pytest.mark.parametrize('overlay', [False, True], ids=['default', 'overlay'])
def test_legacy_exports_work_in_either_import_order(
    tmp_path: Path, legacy_package: tuple[str, str, Path], *, legacy_first: bool, overlay: bool
) -> None:
    """Both import orders must expose the same default or overlaid provider through the legacy package.

    Importing either path is quiet; looking up an old export emits the migration warning.
    """
    package, provider, root = legacy_package
    pythonpath = [root]
    if overlay:
        pythonpath.append(_overlay(tmp_path, package=package, provider=provider))

    def check(*, package: str, provider: str, legacy_first: bool, use_overlay: bool) -> None:
        import warnings
        from importlib import import_module

        provider_name = f'{package}.{provider}'
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            if legacy_first:
                legacy = import_module(package)
                concrete = import_module(provider_name)
            else:
                concrete = import_module(provider_name)
                legacy = import_module(package)
            assert len(caught) == 0, caught

            assert legacy.records is concrete.records
            assert legacy.records() == ([2] if use_overlay else [1])
            assert any(f'importing {package} is DEPRECATED' in str(w.message) for w in caught)
            assert any(f'Instead, import from {provider_name}' in str(w.message) for w in caught)

    _run(
        tmp_path,
        check,
        pythonpath=pythonpath,
        source_file=True,
        package=package,
        provider=provider,
        legacy_first=legacy_first,
        use_overlay=overlay,
    )


@pytest.fixture
def legacy_package(tmp_path: Path) -> tuple[str, str, Path]:
    """Create a synthetic namespace package with a legacy shim, a provider, and an independent sibling."""
    package = 'my.legacy_example'
    provider = 'provider'
    root = tmp_path / 'base'
    directory = root.joinpath(*package.split('.'))
    directory.mkdir(parents=True)
    (directory / '__init__.py').write_text(
        dedent(
            f'''
            from my.core.hpi_compat import handle_legacy_import

            handle_legacy_import(
                parent_module_name=__name__,
                legacy_submodule_name={provider!r},
                parent_module_path=__path__,
            )
            '''
        )
    )

    def records() -> list[int]:
        return [1]

    (directory / f'{provider}.py').write_text(dedent(inspect.getsource(records)) + '\n_hidden = 42\n')
    (directory / 'common.py').write_text('value = 123\n')
    return package, provider, root


def _overlay(tmp_path: Path, *, package: str, provider: str) -> Path:
    """Provide distinct records from a second namespace root to test overlay precedence."""
    root = tmp_path / 'overlay'
    directory = root.joinpath(*package.split('.'))
    directory.mkdir(parents=True)

    def records() -> list[int]:
        return [2]

    (directory / f'{provider}.py').write_text(dedent(inspect.getsource(records)))
    return root


@pytest.mark.parametrize(
    'statement',
    [
        'import {package}.{provider} as concrete',
        'from {package} import {provider} as concrete',
        '''
        if True:
            from .{short} import (
                {provider} as concrete,
            )
        ''',
    ],
    ids=['direct', 'from-package', 'relative-indented-multiline'],
)
def test_canonical_imports_are_quiet_without_caller_source(
    tmp_path: Path, legacy_package: tuple[str, str, Path], statement: str
) -> None:
    """Canonical imports must not warn based on their spelling or the availability of caller source."""
    package, provider, root = legacy_package
    statement = dedent(statement).format(package=package, provider=provider, short=package.removeprefix('my.'))

    def check(*, statement: str) -> None:
        import warnings
        from typing import Any

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            # Import paths vary between cases, so only the import statement remains generated code.
            namespace: dict[str, Any] = {'__package__': 'my'}
            exec(statement, namespace)
            assert namespace['concrete'].records() == [1]
            assert len(caught) == 0, caught

    _run(tmp_path, check, pythonpath=[root], statement=statement)


def test_package_and_sibling_imports_do_not_load_legacy_dependencies(
    tmp_path: Path, legacy_package: tuple[str, str, Path]
) -> None:
    """A missing provider dependency must not prevent importing its parent package or a sibling.

    Accessing an old export must still propagate the original dependency error.
    """
    package, provider, root = legacy_package
    root.joinpath(*package.split('.'), f'{provider}.py').write_text('import hpi_test_missing_dependency\n')

    def check(*, package: str, provider: str) -> None:
        import importlib
        import sys
        import warnings
        from typing import Any

        import pytest

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            legacy = importlib.import_module(package)
            namespace: dict[str, Any] = {}
            exec(f'from {package} import common', namespace)
            assert namespace['common'].value == 123
            assert getattr(legacy, '__wrapped__', None) is None
            assert f'{package}.{provider}' not in sys.modules
            assert len(caught) == 0, caught

            with pytest.raises(ModuleNotFoundError) as error:
                _ = legacy.records
            assert error.value.name == 'hpi_test_missing_dependency'

    _run(tmp_path, check, pythonpath=[root], package=package, provider=provider)


@pytest.mark.parametrize('explicit_all', [False, True])
def test_legacy_from_and_star_imports_follow_provider_exports(
    tmp_path: Path, legacy_package: tuple[str, str, Path], *, explicit_all: bool
) -> None:
    """Legacy imports and dir() must honor the provider's export list, including explicitly exported private names.

    Missing or excluded attributes must not emit deprecation warnings.
    """
    package, provider, root = legacy_package
    if explicit_all:
        path = root.joinpath(*package.split('.'), f'{provider}.py')
        path.write_text(path.read_text() + "__all__ = ['records', '_hidden']\nunexported = 123\n")

    def check(*, package: str, explicit_all: bool) -> None:
        import importlib
        import warnings
        from typing import Any

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            namespace: dict[str, Any] = {}
            exec(f'from {package} import records', namespace)
            records = namespace['records']
            assert records() == [1]
            assert any(f'importing {package} is DEPRECATED' in str(w.message) for w in caught)

            caught.clear()
            namespace.clear()
            exec(f'from {package} import *', namespace)
            assert namespace['records'] is records
            assert ('_hidden' in namespace) == explicit_all
            assert 'unexported' not in namespace
            assert any(f'importing {package} is DEPRECATED' in str(w.message) for w in caught)

            legacy = importlib.import_module(package)
            assert 'records' in dir(legacy)
            assert ('_hidden' in dir(legacy)) == explicit_all
            assert 'unexported' not in dir(legacy)
            caught.clear()
            assert not hasattr(legacy, 'missing')
            assert not hasattr(legacy, 'unexported')
            assert len(caught) == 0, caught

    _run(tmp_path, check, pythonpath=[root], package=package, explicit_all=explicit_all)


def test_legacy_exports_remain_visible_to_cli_discovery(tmp_path: Path, legacy_package: tuple[str, str, Path]) -> None:
    """HPI must find forwarded functions both by explicit query name and by automatic provider discovery."""
    package, provider, root = legacy_package

    def check(*, package: str, provider: str) -> None:
        import importlib
        import warnings

        from my.core.__main__ import _locate_functions_or_prompt
        from my.core.query import locate_qualified_function
        from my.core.stats import _guess_data_providers

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            legacy = importlib.import_module(package)
            concrete = importlib.import_module(f'{package}.{provider}')
            assert _guess_data_providers(legacy) == {'records': concrete.records}
            assert locate_qualified_function(f'{package}.records') is concrete.records
            assert list(_locate_functions_or_prompt([package], prompt=False)) == [concrete.records]
            assert any(f'importing {package} is DEPRECATED' in str(w.message) for w in caught)

    _run(tmp_path, check, pythonpath=[root], package=package, provider=provider)


def test_completion_does_not_silence_later_legacy_access(tmp_path: Path, legacy_package: tuple[str, str, Path]) -> None:
    """A quiet lookup during shell completion must not suppress the warning on later ordinary access."""
    package, _provider, root = legacy_package

    def check(*, package: str) -> None:
        import importlib
        import os
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            legacy = importlib.import_module(package)
            os.environ['_HPI_COMPLETE'] = 'bash_complete'
            assert legacy.records() == [1]
            assert len(caught) == 0, caught
            del os.environ['_HPI_COMPLETE']
            assert legacy.records() == [1]
            assert any(f'importing {package} is DEPRECATED' in str(w.message) for w in caught)

    _run(tmp_path, check, pythonpath=[root], package=package)


def test_package_reload_preserves_overlay_precedence_and_live_exports(
    tmp_path: Path, legacy_package: tuple[str, str, Path]
) -> None:
    """Reloading the shim must preserve overlay priority, and forwarded attributes must reflect provider updates."""
    package, provider, root = legacy_package
    overlay = _overlay(tmp_path, package=package, provider=provider)

    def check(*, package: str, provider: str) -> None:
        import importlib

        legacy = importlib.import_module(package)
        paths = list(legacy.__path__)
        importlib.reload(legacy)
        assert list(legacy.__path__) == paths
        assert legacy.records() == [2]
        concrete = importlib.import_module(f'{package}.{provider}')
        vars(concrete)['records'] = lambda: [3]
        assert legacy.records() == [3]

    _run(tmp_path, check, pythonpath=[root, overlay], package=package, provider=provider)
