import os
from pathlib import Path

from more_itertools import bucket
import pytest


from my.core.cfg import tmp_config

from my.coding.commits import commits


pytestmark = pytest.mark.skipif(
    os.name == 'nt',
    reason='TODO figure out how to install fd-find on Windows',
)


def test() -> None:
    all_commits = list(commits())
    assert len(all_commits) > 100

    buckets = bucket(all_commits, key=lambda c: c.repo)
    by_repo = {k: list(buckets[k]) for k in buckets}
    # handle later


@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    # TODO maybe test against actual testdata, could check for
    # - datetime handling
    # - bare repos
    # - canonical name
    # - caching?
    hpi_repo_root = Path(__file__).absolute().parent.parent.parent
    assert (hpi_repo_root / '.git').exists(), hpi_repo_root

    class config:
        class commits:
            emails = {'karlicoss@gmail.com'}
            names = {'Dima'}
            roots = [hpi_repo_root]

    with tmp_config(modules='my.coding.commits', config=config):
        yield
