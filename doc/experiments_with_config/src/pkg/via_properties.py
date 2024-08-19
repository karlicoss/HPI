from abc import abstractmethod

class config:
    @property
    @abstractmethod
    def export_path(self) -> str:
        raise NotImplementedError

    @property
    def cache_path(self) -> str | None:
        return None


def make_config() -> config:
    from pkg.config import module_config as user_config

    # NOTE: order is important -- attributes would be added in reverse order
    #   e.g. first from config, then from user_config -- just what we want
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
