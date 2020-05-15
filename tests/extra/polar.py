from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()


import pytest # type: ignore

# todo maybe search fot info.json recursively?
@pytest.mark.parametrize('dotpolar', [
    '',
    'data/polar/BojanKV_polar/.polar',
    'data/polar/TheCedarPrince_KnowledgeRepository',
    'data/polar/coelias_polardocs',
    'data/polar/warkdarrior_polar-document-repository'
])
def test_hpi(dotpolar: str):
    if dotpolar != '':
        pdir = Path(ROOT / dotpolar)
        class user_config:
            export_dir = pdir

        import my.config
        setattr(my.config, 'polar', user_config)

    import sys
    M = 'my.reading.polar'
    if M in sys.modules:
        del sys.modules[M]
    # TODO maybe set config directly against polar module?

    import my.reading.polar as polar
    from my.reading.polar import get_entries
    assert len(list(get_entries())) > 10
