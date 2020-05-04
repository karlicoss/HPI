from pathlib import Path


def setup_notes_path(notes: Path) -> None:
    # TODO reuse doc from my.cfg?
    from my.cfg import config

    from types import SimpleNamespace
    config.orgmode = SimpleNamespace( # type: ignore[misc,assignment]
        roots=[notes],
    )


def test_dynamic_configuration(notes: Path) -> None:
    setup_notes_path(notes)

    from my.body.weight import dataframe
    weight_df = dataframe()

    assert list(weight_df['weight'].fillna(0.0)) == [
        0.0,
        62.0,
        0.0,
        61.0,
        62.0,
        0.0,
    ]


import pytest # type: ignore
@pytest.fixture
def notes(tmp_path: Path):
    ndir = tmp_path / 'notes'
    ndir.mkdir()
    logs = ndir / 'logs.org'
    logs.write_text('''
#+TITLE: Stuff I'm logging

* Weight (org-capture) :weight:
** [2020-05-01 Fri 09:00] 62
** 63
    this should be ignored, got no timestmap
** [2020-05-03 Sun 08:00] 61
** [2020-05-04 Mon 10:00] 62
    ''')
    misc = ndir / 'misc.org'
    misc.write_text('''
Some misc stuff

* unrelated note :weight:whatever:
    ''')
    try:
        yield ndir
    finally:
        pass


# TODO test set_repo?
