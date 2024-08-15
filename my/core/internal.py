"""
Utils specific to hpi core, shouldn't really be used by HPI modules
"""


def assert_subpackage(name: str) -> None:
    # can lead to some unexpected issues if you 'import cachew' which being in my/core directory.. so let's protect against it
    # NOTE: if we use overlay, name can be smth like my.origg.my.core.cachew ...
    assert name == '__main__' or 'my.core' in name, f'Expected module __name__ ({name}) to be __main__ or start with my.core'
