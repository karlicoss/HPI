"""
Currently 'preferred' way of defining configs as of 20240818
"""
from dataclasses import dataclass

from pkg.config import module_config as user_config


@dataclass
class config(user_config):
    export_path: str

    cache_path: str | None = None


def run() -> None:
    print('hello from', __name__)

    cfg = config

    # check a required attribute
    print(f'{cfg.export_path=}')

    # check a non-required attribute with default value
    print(f'{cfg.cache_path=}')

    # check a 'dynamically' defined attribute in user config
    print(f'{cfg.custom_setting=}')

