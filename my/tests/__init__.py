# hmm, sadly pytest --import-mode importlib --pyargs my.core.tests doesn't work properly without __init__.py
# although it works if you run either my.core or my.core.tests.sqlite (for example) directly
# so if it gets in the way could get rid of this later?

# this particularly sucks here, because otherwise would be nice if people could also just put tests for their my. packages into their tests/ directory
# maybe some sort of hack could be used later similar to handle_legacy_import?

from my.core import __NOT_HPI_MODULE__
