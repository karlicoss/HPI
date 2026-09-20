from importlib import import_module
from types import SimpleNamespace
from typing import Literal

import pytest


@pytest.mark.parametrize(
    ('module_name', 'config_path', 'required_attribute'),
    [
        ('my.github.gdpr', 'github', 'gdpr_dir'),
        ('my.google.takeout.paths', 'google', 'takeout_path'),
        ('my.twitter.archive', 'twitter_archive', 'export_path'),
        ('my.twitter.talon', 'twitter.talon', 'export_path'),
        ('my.zulip.organization', 'zulip.organization', 'export_path'),
    ],
)
@pytest.mark.parametrize('value_kind', ['missing', 'attribute', 'property'])
def test_required_config_property(
    *,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    config_path: str,
    required_attribute: str,
    value_kind: Literal['missing', 'attribute', 'property'],
) -> None:
    import my.config

    module = import_module(module_name)
    expected = '/path/to/export'
    accesses = 0

    class user_config:
        pass

    def get_path(self: object) -> str:
        nonlocal accesses
        accesses += 1
        return expected

    if value_kind == 'attribute':
        setattr(user_config, required_attribute, expected)
    elif value_kind == 'property':
        setattr(user_config, required_attribute, property(get_path))

    section, *nested = config_path.split('.')
    config_value: object = user_config
    for name in reversed(nested):
        config_value = SimpleNamespace(**{name: config_value})
    monkeypatch.setattr(my.config, section, config_value)

    if value_kind == 'missing':
        with pytest.raises(TypeError, match=required_attribute):
            module.make_config()
        return

    cfg = module.make_config()
    assert accesses == 0
    assert getattr(cfg, required_attribute) == expected
    assert accesses == (1 if value_kind == 'property' else 0)
