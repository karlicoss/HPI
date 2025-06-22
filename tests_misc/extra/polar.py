import sys
from importlib import reload
from pathlib import Path

from my.core.common import get_valid_filename

ROOT = Path(__file__).parent.absolute()
OUTPUTS = ROOT / 'outputs'


import pytest


def test_hpi(prepare: str) -> None:
    from my.polar import get_entries
    assert len(list(get_entries())) > 1

def test_orger(prepare: str, tmp_path: Path) -> None:
    from my.core.utils.imports import import_file, import_from
    om = import_file(ROOT / 'orger/modules/polar.py')
    # reload(om)

    pv = om.PolarView()
    # TODO hmm. worth making public?
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / (get_valid_filename(prepare) + '.org')
    pv._run(to=out)


PARAMS = [
    # 'data/polar/BojanKV_polar/.polar',
    '',
    # 'data/polar/TheCedarPrince_KnowledgeRepository',
    # 'data/polar/coelias_polardocs',
    # 'data/polar/warkdarrior_polar-document-repository'
]

@pytest.fixture(params=PARAMS)
def prepare(request):
    dotpolar = request.param
    class user_config:
        if dotpolar != '': # default
            polar_dir = Path(ROOT / dotpolar)
        defensive = False

    import my.config
    setattr(my.config, 'polar', user_config)

    import my.polar as polar
    reload(polar)
    # TODO hmm... ok, need to document reload()
    return dotpolar
