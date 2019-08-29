#!/usr/bin/env python3
from pathlib import Path
import codecs
from multiprocessing.pool import Pool
from subprocess import CompletedProcess
import sys
import io
from typing import NamedTuple, List, Optional
from contextlib import redirect_stderr
import logging
from pprint import pprint
import itertools

from kython import import_file
from kython.klogging import setup_logzero


from ..ext.pdfannots import pdfannots # type: ignore

from .private import ROOT_PATHS, is_handled


def get_logger():
    return logging.getLogger('annotation-crawler')


def get_pdfs() -> List[Path]:
    pdfs = itertools.chain.from_iterable(Path(p).glob('**/*.pdf') for p in ROOT_PATHS)
    return list(sorted(pdfs))


# TODO cachew?
class Result(NamedTuple):
    path: Path
    annotations: List
    stderr: str


class Annotation(NamedTuple):
    author: Optional[str]
    page: int
    highlight: Optional[str]
    comment: Optional[str]


def as_annotation(ann) -> Annotation:
    d = vars(ann)
    d['page'] = ann.page.pageno
    for a in ('boxes', 'rect'):
        if a in d:
            del d[a]
    return Annotation(
        author   =d['author'],
        page     =d['page'],
        highlight=d['text'],
        comment  =d['contents'],
    )


class PdfAnnotsException(Exception):
    def __init__(self, path: Path) -> None:
        self.path = path


def _get_annots(p: Path) -> Result:
    progress = False
    with p.open('rb') as fo:
        f = io.StringIO()
        with redirect_stderr(f):
            (annots, outlines) = pdfannots.process_file(fo, emit_progress=progress)
            # outlines are kinda like TOC, I don't really need them
        return Result(
            path=p,
            annotations=list(map(as_annotation, annots)),
            stderr=f.getvalue(),
        )


def get_annots(p: Path) -> Result:
    try:
        return _get_annots(p)
    except Exception as e:
        raise PdfAnnotsException(p) from e


def test():
    res = get_annots(Path('/L/zzz_syncthing/TODO/TOREAD/done/mature-optimization_wtf.pdf'))
    assert len(res.annotations) > 0


def test2():
    res = get_annots(Path('/L/zzz_borg/downloads/nonlinear2.pdf'))
    print(res)


def main():
    logger = get_logger()
    setup_logzero(logger, level=logging.DEBUG)

    pdfs = get_pdfs()
    logger.info('processing %d pdfs', len(pdfs))

    unhandled = []
    errors = []
    def callback(res: Result):
        if is_handled(res.path):
            return
        logger.info('processed %s', res.path)

        if len(res.stderr) > 0:
            err = 'while processing %s: %s' % (res.path, res.stderr)
            logger.error(err)
            errors.append(err)
        elif len(res.annotations) > 0:
            logger.warning('unhandled: %s', res)
            unhandled.append(res)

    def error_cb(err):
        if isinstance(err, PdfAnnotsException):
            if is_handled(err.path):
                # TODO log?
                return
            logger.error('while processing %s', err.path)
            err = err.__cause__
        logger.exception(err)
        errors.append(str(err))

    with Pool() as p:
        handles = [p.apply_async(
            get_annots,
            (pdf, ),
            callback=callback,
            error_callback=error_cb,
        ) for pdf in pdfs if not is_handled(pdf)] # TODO log if we skip?
        for h in handles:
            h.wait()

    if len(unhandled) > 0:
        for r in unhandled:
            logger.warning('unhandled annotations in: %s', r.path)
            for a in r.annotations:
                pprint(a)
        sys.exit(1)

    if len(errors) > 0:
        logger.error('had %d errors while processing', len(errors))
        sys.exit(2)



if __name__ == '__main__':
    main()
