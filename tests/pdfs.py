import inspect
from pathlib import Path
import tempfile

from my.pdfs import get_annots, annotated_pdfs

from .common import testdata

EXPECTED_HIGHLIGHTS = {
    'Since 1994, when we first began organizing web sites, we have enjoyed a rare opportunity to participate in the birth of a new discipline. ',
    'And yet, unlearn we must, ',
    '',
}


def test_get_annots() -> None:
    """
    Test get_annots, with a real PDF file
    get_annots should return a list of three Annotation objects
    """
    annotations = get_annots(testdata() / 'pdfs' / 'Information Architecture for the World Wide Web.pdf')
    assert len(annotations) == 3
    assert set([a.highlight for a in annotations]) == EXPECTED_HIGHLIGHTS


def test_annotated_pdfs_with_filelist() -> None:
    """
    Test annotated_pdfs, with a real PDF file
    annotated_pdfs should return a list of one Pdf object, with three Annotations
    """
    filelist = [testdata() / 'pdfs' / 'Information Architecture for the World Wide Web.pdf']
    annotations_generator = annotated_pdfs(filelist=filelist, roots=None)

    assert inspect.isgeneratorfunction(annotated_pdfs)

    highlights_from_pdfs = []

    for pdf_object in list(annotations_generator):
        assert not isinstance(pdf_object, Exception)
        highlights_from_pdfs.extend([a.highlight for a in pdf_object.annotations])

    assert len(highlights_from_pdfs) == 3
    assert set(highlights_from_pdfs) == EXPECTED_HIGHLIGHTS
