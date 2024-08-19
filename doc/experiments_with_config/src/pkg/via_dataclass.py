from dataclasses import dataclass


@dataclass
class config:
    export_path: str
    cache_path: str | None = None


def make_config() -> config:
    from pkg.config import module_config as user_config

    # NOTE: order is important -- attributes would be added in reverse order
    #   e.g. first from config, then from user_config -- just what we want
    # NOTE: in theory, this works without @dataclass annotation on combined_config
    #   however, having @dataclass adds extra type checks about missing required attributes
    #   when we instantiate combined_config
    @dataclass
    class combined_config(user_config, config): ...

    return combined_config()


def run() -> None:
    print('hello from', __name__)

    cfg = make_config()

    # check a required attribute
    print(f'{cfg.export_path=}')

    # check a non-required attribute with default value
    print(f'{cfg.cache_path=}')

    # check a 'dynamically' defined attribute in user config
    # NOTE: mypy fails as it has no static knowledge of the attribute
    #   but kinda expected, not much we can do
    print(f'{cfg.custom_setting=}')  # type: ignore[attr-defined]
