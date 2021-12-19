from pathlib import Path

from more_itertools import ilen

import pytest

from .common import testdata


def test_module(with_config) -> None:
    # TODO crap. if module is imported too early (on the top level, it makes it super hard to overrride config)
    # need to at least detect it...
    from my.pdfs import annotations, annotated_pdfs

    # todo check types etc as well
    assert ilen(annotations()) >= 3
    assert ilen(annotated_pdfs()) >= 1


def test_with_error(with_config, tmp_path: Path) -> None:
    """should handle crappy files gracefully"""
    root = tmp_path
    g = root / 'garbage.pdf'
    g.write_text('garbage')
    from my.config import pdfs
    del pdfs.roots  # meh. otherwise legacy config value 'wins'
    pdfs.paths = (root,)

    from my.pdfs import annotations
    annots = list(annotations())
    [annot] = annots
    assert isinstance(annot, Exception)


@pytest.fixture
def with_config():
    from .common import reset_modules
    reset_modules()  # todo ugh.. getting boilerplaty.. need to make it a bit more automatic..

    # extra_data = Path(__file__).absolute().parent / 'extra/data/polar'
    # assert extra_data.exists(), extra_data
    # todo hmm, turned out no annotations in these ones.. whatever

    class user_config:
        roots = [
            testdata(),
        ]

    import my.core.cfg as C
    with C.tmp_config() as config:
        config.pdfs = user_config  # type: ignore
        try:
            yield
        finally:
            reset_modules()


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
    from my.pdfs import get_annots

    annotations = get_annots(testdata() / 'pdfs' / 'Information Architecture for the World Wide Web.pdf')
    assert len(annotations) == 3
    assert set([a.highlight for a in annotations]) == EXPECTED_HIGHLIGHTS


def test_annotated_pdfs_with_filelist() -> None:
    """
    Test annotated_pdfs, with a real PDF file
    annotated_pdfs should return a list of one Pdf object, with three Annotations
    """
    from my.pdfs import annotated_pdfs

    filelist = [testdata() / 'pdfs' / 'Information Architecture for the World Wide Web.pdf']
    annotations_generator = annotated_pdfs(filelist=filelist)

    import inspect
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
