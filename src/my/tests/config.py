import warnings
from importlib import import_module
from types import SimpleNamespace
from typing import Literal

import pytest


@pytest.mark.parametrize(
    ('module_name',                    'config_path',             'required_attribute', 'legacy_attribute'),
    [
        ('my.endomondo.endoexport',    'endomondo.endoexport',    'export_path',        None),
        ('my.github.gdpr',             'github',                  'gdpr_dir',           None),
        ('my.github.ghexport',         'github',                  'export_path',        None),
        ('my.hypothesis.hypexport',    'hypothesis.hypexport',    'export_path',        None),
        ('my.instapaper.instapexport', 'instapaper.instapexport', 'export_path',        None),
        ('my.jawbone.api',             'jawbone',                 'export_path',        'export_dir'),
        ('my.kobo.kobuddy',            'kobo.kobuddy',            'export_path',        None),
        ('my.pinboard.pinbexport',     'pinboard.pinbexport',     'export_path',        None),
        ('my.pocket.pockexport',       'pocket.pockexport',       'export_path',        None),
        ('my.reddit.rexport',          'reddit.rexport',          'export_path',        None),
        ('my.rescuetime.rescuexport',  'rescuetime.rescuexport',  'export_path',        None),
        ('my.twitter.archive',         'twitter_archive',         'export_path',        None),
        ('my.twitter.talon',           'twitter.talon',           'export_path',        None),
        ('my.zulip.organization',      'zulip.organization',      'export_path',        None),
    ],
)  # fmt: skip
@pytest.mark.parametrize('value_kind', ['missing', 'attribute', 'property'])
def test_required_config_property(
    *,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    config_path: str,
    required_attribute: str,
    legacy_attribute: str | None,
    value_kind: Literal['missing', 'attribute', 'property'],
) -> None:
    """Required settings accept plain attributes or lazy properties and fail when absent."""
    import my.config

    module = import_module(module_name)
    expected = '/path/to/export'
    accesses = 0

    class user_config:
        exprot_path = expected

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
        if legacy_attribute is None:
            with pytest.raises(TypeError, match=required_attribute):
                module.make_config()
        else:
            cfg = module.make_config()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                with pytest.raises(AttributeError, match=required_attribute) as error:
                    getattr(cfg, required_attribute)
            assert error.value.name == required_attribute
            assert caught == []
        return

    cfg = module.make_config()
    assert accesses == 0
    assert getattr(cfg, required_attribute) == expected
    assert accesses == (1 if value_kind == 'property' else 0)
