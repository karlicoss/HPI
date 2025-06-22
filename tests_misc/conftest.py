import pytest


# I guess makes sense by default
@pytest.fixture(autouse=True)
def without_cachew():
    from my.core.cachew import disabled_cachew
    with disabled_cachew():
        yield
