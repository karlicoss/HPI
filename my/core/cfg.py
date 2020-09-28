from typing import TypeVar, Type, Callable, Dict, Any

Attrs = Dict[str, Any]

C = TypeVar('C')

# todo not sure about it, could be overthinking...
# but short enough to change later
# TODO document why it's necessary?
def make_config(cls: Type[C], migration: Callable[[Attrs], Attrs]=lambda x: x) -> C:
    props = dict(vars(cls.__base__))
    props = migration(props)
    from dataclasses import fields
    params = {
        k: v
        for k, v in props.items()
        if k in {f.name for f in fields(cls)}
    }
    return cls(**params) # type: ignore[call-arg]


F = TypeVar('F')
from contextlib import contextmanager
import inspect
from typing import Iterator
@contextmanager
def override_config(config: F) -> Iterator[F]:
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
