import inspect
from pathlib import Path

import pytest
from more_itertools import ilen

from my.core.cfg import tmp_config
from my.pdfs import annotated_pdfs, annotations, get_annots

from .common import testdata


def test_module(with_config) -> None:
    # todo check types etc as well
    assert ilen(annotations()) >= 3
    assert ilen(annotated_pdfs()) >= 1


def test_with_error(with_config, tmp_path: Path) -> None:
    """should handle crappy files gracefully"""
    root = tmp_path
    g = root / 'garbage.pdf'
    g.write_text('garbage')

    from my.config import pdfs

    # meh. otherwise legacy config value 'wins'
    del pdfs.roots  # type: ignore[attr-defined]
    pdfs.paths = (root,)

    annots = list(annotations())
    [annot] = annots
    assert isinstance(annot, Exception)


@pytest.fixture
def with_config():
    # extra_data = Path(__file__).absolute().parent / 'extra/data/polar'
    # assert extra_data.exists(), extra_data
    # todo hmm, turned out no annotations in these ones.. whatever

    class user_config:
        roots = [
            testdata(),
        ]

    with tmp_config() as config:
        config.pdfs = user_config
        yield


EXPECTED_HIGHLIGHTS = {
    'Since 1994, when we first began organizing web sites, we have enjoyed a rare oppor-tunity to participate in the birth of a new discipline.',
    'And yet, unlearn we must,',
    '',
}


def test_get_annots() -> None:
    """
    Test get_annots, with a real PDF file
    get_annots should return a list of three Annotation objects
    """
    annotations = get_annots(testdata() / 'pdfs' / 'Information Architecture for the World Wide Web.pdf')
    assert len(annotations) == 3
    assert {a.highlight for a in annotations} == EXPECTED_HIGHLIGHTS


def test_annotated_pdfs_with_filelist() -> None:
    """
    Test annotated_pdfs, with a real PDF file
    annotated_pdfs should return a list of one Pdf object, with three Annotations
    """
    filelist = [testdata() / 'pdfs' / 'Information Architecture for the World Wide Web.pdf']
    annotations_generator = annotated_pdfs(filelist=filelist)

    assert inspect.isgeneratorfunction(annotated_pdfs)

    highlights_from_pdfs = []

    for pdf_object in list(annotations_generator):
        assert not isinstance(pdf_object, Exception)
        highlights_from_pdfs.extend([a.highlight for a in pdf_object.annotations])

    assert len(highlights_from_pdfs) == 3
    assert set(highlights_from_pdfs) == EXPECTED_HIGHLIGHTS


# todo old test on my(karlicoss) computer:
# - mature-optimization_wtf.pdf: >3 annotations?
# - nonlinear2.pdf
