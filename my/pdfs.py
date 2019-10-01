#!/usr/bin/env python3
from . import paths
from .common import import_file

from pathlib import Path


# path to pdfannots (https://github.com/0xabu/pdfannots)
pdfannots = import_file(paths.pdfs.pdfannots_py)


from datetime import datetime
import re
from subprocess import CompletedProcess
import sys
import io
from typing import NamedTuple, List, Optional
from contextlib import redirect_stderr
import logging


def get_logger():
    return logging.getLogger('my.pdfs')


def get_candidates(roots=None) -> List[Path]:
    if roots is None:
        roots = paths.pdfs.roots

    import itertools
    pdfs = itertools.chain.from_iterable(Path(p).glob('**/*.pdf') for p in roots)
    return list(sorted(pdfs))


def is_ignored(p):
    return paths.pdfs.is_ignored(p)


# TODO cachew?
class Annotation(NamedTuple):
    author: Optional[str]
    page: int
    highlight: Optional[str]
    comment: Optional[str]
    date: Optional[datetime]


class Pdf(NamedTuple):
    path: Path
    annotations: List[Annotation]
    stderr: str

    @property
    def date(self):
        return self.annotations[-1].date


def as_annotation(ann) -> Annotation:
    d = vars(ann)
    d['page'] = ann.page.pageno
    for a in ('boxes', 'rect'):
        if a in d:
            del d[a]
    dates = d['date']
    date: Optional[datetime] = None
    if dates is not None:
        dates = dates.replace("'", "")
        # 20190630213504+0100
        dates = re.sub('Z0000$', '+0000', dates)
        FMT = '%Y%m%d%H%M%S'
        # TODO is it utc if there is not timestamp?
        for fmt in [FMT, FMT + '%z']:
            try:
                date = datetime.strptime(dates, fmt)
                break
            except ValueError:
                pass
        else:
            raise RuntimeError(dates)
    return Annotation(
        author   =d['author'],
        page     =d['page'],
        highlight=d['text'],
        comment  =d['contents'],
        date     =date,
    )


class PdfAnnotsException(Exception):
    def __init__(self, path: Path) -> None:
        self.path = path


def _get_annots(p: Path) -> Pdf:
    progress = False
    with p.open('rb') as fo:
        f = io.StringIO()
        with redirect_stderr(f):
            (annots, outlines) = pdfannots.process_file(fo, emit_progress=progress)
            # outlines are kinda like TOC, I don't really need them
    return Pdf(
        path=p,
        annotations=list(map(as_annotation, annots)),
        stderr=f.getvalue(),
    )


def get_annots(p: Path) -> Pdf:
    try:
        return _get_annots(p)
    except Exception as e:
        raise PdfAnnotsException(p) from e


def get_annotated_pdfs(roots=None) -> List[Pdf]:
    logger = get_logger()

    pdfs = get_candidates(roots=roots)
    logger.info('processing %d pdfs', len(pdfs))

    collected = []
    errors = []
    def callback(res: Pdf):
        if is_ignored(res.path):
            return
        logger.info('processed %s', res.path)

        if len(res.stderr) > 0:
            err = 'while processing %s: %s' % (res.path, res.stderr)
            logger.error(err)
            errors.append(err)
        elif len(res.annotations) > 0:
            logger.info('collected %s annotations', len(res.annotations))
            collected.append(res)

    def error_cb(err):
        if isinstance(err, PdfAnnotsException):
            if is_ignored(err.path):
                # TODO log?
                return
            logger.error('while processing %s', err.path)
            err = err.__cause__
        logger.exception(err)
        errors.append(str(err))

    from multiprocessing.pool import Pool
    with Pool() as p:
        handles = [p.apply_async(
            get_annots,
            (pdf, ),
            callback=callback,
            error_callback=error_cb,
        ) for pdf in pdfs if not is_ignored(pdf)] # TODO log if we skip?
        for h in handles:
            h.wait()

    # TODO more defensive error processing?
    if len(errors) > 0:
        logger.error('had %d errors while processing', len(errors))
        sys.exit(2)

    return collected


def test():
    res = get_annots(Path('/L/zzz_syncthing/TODO/TOREAD/done/mature-optimization_wtf.pdf'))
    assert len(res.annotations) > 0


def test2():
    res = get_annots(Path('/L/zzz_borg/downloads/nonlinear2.pdf'))
    print(res)


def main():
    from pprint import pprint

    logger = get_logger()
    from kython.klogging import setup_logzero
    setup_logzero(logger, level=logging.DEBUG)

    collected = get_annotated_pdfs()
    if len(collected) > 0:
        for r in collected:
            logger.warning('collected annotations in: %s', r.path)
            for a in r.annotations:
                pprint(a)
