from typing import TypeVar, Type, Callable, Dict, Any

Attrs = Dict[str, Any]

C = TypeVar('C')

# todo not sure about it, could be overthinking...
# but short enough to change later
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
