from ..cfg import tmp_config


def _init_default_config() -> None:
    import my.config

    class default_config:
        count = 5

    my.config.simple = default_config  # type: ignore[assignment,misc]


def test_tmp_config() -> None:
    ## ugh. ideally this would be on the top level (would be a better test)
    ## but pytest imports everything first, executes hooks, and some reset_modules() fictures mess stuff up
    ## later would be nice to be a bit more careful about them
    _init_default_config()
    from my.simple import items

    assert len(list(items())) == 5

    class config:
        class simple:
            count = 3

    with tmp_config(modules='my.simple', config=config):
        assert len(list(items())) == 3

    assert len(list(items())) == 5
