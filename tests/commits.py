# TODO need fdfind on CI?
from pathlib import Path

from more_itertools import bucket
import pytest


def test() -> None:
    from my.coding.commits import commits
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
    hpi_repo_root = Path(__file__).absolute().parent.parent
    assert (hpi_repo_root / '.git').exists(), hpi_repo_root

    class commits:
        emails = {'karlicoss@gmail.com'}
        names = {'Dima'}
        roots = [hpi_repo_root]

    from my.core.cfg import tmp_config
    with tmp_config() as config:
        config.commits = commits
        yield
