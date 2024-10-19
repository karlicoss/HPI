from __future__ import annotations

import importlib
import re
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import Any, Callable, TypeVar

Attrs = dict[str, Any]

C = TypeVar('C')


# todo not sure about it, could be overthinking...
# but short enough to change later
# TODO document why it's necessary?
def make_config(cls: type[C], migration: Callable[[Attrs], Attrs] = lambda x: x) -> C:
    user_config = cls.__base__
    old_props = {
        # NOTE: deliberately use gettatr to 'force' class properties here
        k: getattr(user_config, k)
        for k in vars(user_config)
    }
    new_props = migration(old_props)
    from dataclasses import fields

    params = {
        k: v
        for k, v in new_props.items()
        if k in {f.name for f in fields(cls)}  # type: ignore[arg-type]  # see https://github.com/python/typing_extensions/issues/115
    }
    # todo maybe return type here?
    return cls(**params)


F = TypeVar('F')


@contextmanager
def _override_config(config: F) -> Iterator[F]:
    '''
    Temporary override for config's parameters, useful for testing/fake data/etc.
    '''
    orig_properties = {k: v for k, v in vars(config).items() if not k.startswith('__')}
    try:
        yield config
    finally:
        # ugh. __dict__ of type objects isn't writable..
        for k, v in orig_properties.items():
            setattr(config, k, v)
        added = {k for k in set(vars(config).keys()).difference(set(orig_properties.keys())) if not k.startswith('__')}
        for k in added:
            delattr(config, k)


ModuleRegex = str


@contextmanager
def _reload_modules(modules: ModuleRegex) -> Iterator[None]:
    # need to use list here, otherwise reordering with set might mess things up
    def loaded_modules() -> list[str]:
        return [name for name in sys.modules if re.fullmatch(modules, name)]

    modules_before = loaded_modules()

    # uhh... seems that reversed might make more sense -- not 100% sure why, but this works for tests/reddit.py
    for m in reversed(modules_before):
        # ugh... seems that reload works whereas pop doesn't work in some cases (e.g. on tests/reddit.py)
        # sys.modules.pop(m, None)
        importlib.reload(sys.modules[m])

    try:
        yield
    finally:
        modules_after = loaded_modules()
        modules_before_set = set(modules_before)
        for m in modules_after:
            if m in modules_before_set:
                # was previously loaded, so need to reload to pick up old config
                importlib.reload(sys.modules[m])
            else:
                # wasn't previously loaded, so need to unload it
                # otherwise it might fail due to missing config etc
                sys.modules.pop(m, None)


@contextmanager
def tmp_config(*, modules: ModuleRegex | None = None, config=None):
    if modules is None:
        assert config is None
    if modules is not None:
        assert config is not None

    import my.config

    with ExitStack() as module_reload_stack, _override_config(my.config) as new_config:
        if config is not None:
            overrides = {k: v for k, v in vars(config).items() if not k.startswith('__')}
            for k, v in overrides.items():
                setattr(new_config, k, v)

        if modules is not None:
            module_reload_stack.enter_context(_reload_modules(modules))
        yield new_config


def test_tmp_config() -> None:
    class extra:
        data_path = '/path/to/data'

    with tmp_config() as c:
        assert c.google != 'whatever'
        assert not hasattr(c, 'extra')
        c.extra = extra
        c.google = 'whatever'
    # todo hmm. not sure what should do about new properties??
    assert not hasattr(c, 'extra')
    assert c.google != 'whatever'


###
# todo properly deprecate, this isn't really meant for public use
override_config = _override_config
