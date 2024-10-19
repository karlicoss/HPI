from collections.abc import Iterator

from browserexport.merge import Visit, merge_visits

from my.core import Stats
from my.core.source import import_source

src_export = import_source(module_name="my.browser.export")
src_active = import_source(module_name="my.browser.active_browser")


@src_export
def _visits_export() -> Iterator[Visit]:
    from . import export
    return export.history()


@src_active
def _visits_active() -> Iterator[Visit]:
    from . import active_browser
    return active_browser.history()


# NOTE: you can comment out the sources you don't need
def history() -> Iterator[Visit]:
    yield from merge_visits([
        _visits_active(),
        _visits_export(),
    ])


def stats() -> Stats:
    from my.core import stat

    return {**stat(history)}
