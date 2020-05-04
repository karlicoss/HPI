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


def test_set_repo(tmp_path: Path) -> None:
    from my.cfg import config
    from types import SimpleNamespace
    config.hypothesis = SimpleNamespace( # type: ignore[misc,assignment]
        export_path='whatever',
    )

    # precondition:
    # should fail because can't find hypexport
    with pytest.raises(ModuleNotFoundError):
        import my.hypothesis

    fake_hypexport = tmp_path / 'hypexport'
    fake_hypexport.mkdir()
    (fake_hypexport / 'dal.py').write_text('''
Highlight = None
Page = None
DAL = None
    ''')

    from my.cfg import set_repo
    # FIXME meh. hot sure about setting the parent??
    set_repo('hypexport', tmp_path)

    # should succeed now!
    import my.hypothesis
