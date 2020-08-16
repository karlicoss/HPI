#!/usr/bin/env python3
'''
PDF documents and annotations on your filesystem
'''
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import re
import sys
import io
import logging
from pathlib import Path
from typing import NamedTuple, List, Optional, Iterator
from contextlib import redirect_stderr


from .common import mcachew, group_by_key
from .error import Res, split_errors

# path to pdfannots (https://github.com/0xabu/pdfannots)
import my.config.repos.pdfannots.pdfannots as pdfannots
from my.config import pdfs as config


def get_logger():
    return logging.getLogger('my.pdfs')


def is_ignored(p: Path) -> bool:
    """
    Used to ignore some extremely heavy files
    is_ignored function taken either from config,
    or if not defined, it's a function that returns False
    """
    if hasattr(config, 'is_ignored'):
        return config.is_ignored(p)

    # Default
    return lambda x: False


def candidates(filelist=None, roots=None) -> Iterator[Path]:
    if filelist is not None:
        return candidates_from_filelist(filelist)
    else:
        return candidates_from_roots(roots)

def candidates_from_filelist(filelist) -> Iterator[Path]:
    for f in filelist:
        p = Path(f)
        if not is_ignored(p):
            yield p

def candidates_from_roots(roots=None) -> Iterator[Path]:
    if roots is None:
        roots = config.roots

    for r in roots:
        for p in Path(r).rglob('*.pdf'):
            if not is_ignored(p):
                yield p

# TODO canonical names
# TODO defensive if pdf was removed, also cachew key needs to be defensive


class Annotation(NamedTuple):
    path: str
    author: Optional[str]
    page: int
    highlight: Optional[str]
    comment: Optional[str]
    date: Optional[datetime]


def as_annotation(*, raw_ann, path: str) -> Annotation:
    d = vars(raw_ann)
    d['page'] = raw_ann.page.pageno
    for a in ('boxes', 'rect'):
        if a in d:
            del d[a]
    dates = d.get('date')
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
            # TODO defensive?
            raise RuntimeError(dates)
    return Annotation(
        path      = path,
        author    = d['author'],
        page      = d['page'],
        highlight = d['text'],
        comment   = d['contents'],
        date      = date,
    )


def get_annots(p: Path) -> List[Annotation]:
    with p.open('rb') as fo:
        f = io.StringIO()
        with redirect_stderr(f):
            (annots, outlines) = pdfannots.process_file(fo, emit_progress=False)
            # outlines are kinda like TOC, I don't really need them
    return [as_annotation(raw_ann=a, path=str(p)) for a in annots]
    # TODO stderr?


def hash_files(pdfs: List[Path]):
    # if mtime hasn't changed then the file hasn't changed either
    return [(pdf, pdf.stat().st_mtime) for pdf in pdfs]

# TODO might make more sense to be more fine grained here, e.g. cache annotations for indifidual files

@mcachew(hashf=hash_files)
def _iter_annotations(pdfs: List[Path]) -> Iterator[Res[Annotation]]:
    logger = get_logger()

    logger.info('processing %d pdfs', len(pdfs))

    # TODO how to print to stdout synchronously?
    with ProcessPoolExecutor() as pool:
        futures = [
            pool.submit(get_annots, pdf)
            for pdf in pdfs
        ]
        for f, pdf in zip(futures, pdfs):
            try:
                yield from f.result()
            except Exception as e:
                logger.error('While processing %s:', pdf)
                logger.exception(e)
                # TODO not sure if should attach pdf as well; it's a bit annoying to pass around?
                # also really have to think about interaction with cachew...
                yield e


def iter_annotations(filelist=None, roots=None) -> Iterator[Res[Annotation]]:
    pdfs = list(sorted(candidates(filelist=filelist, roots=None)))
    yield from _iter_annotations(pdfs=pdfs)


class Pdf(NamedTuple):
    path: Path
    annotations: List[Annotation]

    @property
    def date(self):
        return self.annotations[-1].date


def annotated_pdfs(filelist=None, roots=None) -> Iterator[Res[Pdf]]:
    it = iter_annotations(filelist=filelist, roots=roots)
    vit, eit = split_errors(it, ET=Exception)

    for k, g in group_by_key(vit, key=lambda a: a.path).items():
        yield Pdf(path=Path(k), annotations=g)
    yield from eit


def test():
    res = get_annots(Path('/L/zzz_syncthing/TODO/TOREAD/done/mature-optimization_wtf.pdf'))
    assert len(res) > 3


def test2():
    res = get_annots(Path('/L/zzz_borg/downloads/nonlinear2.pdf'))
    print(res)


def test_with_error():
    # TODO need example of pdf file...
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        g = root / 'garbage.pdf'
        g.write_text('garbage')
        roots = [
            root,
            # '/usr/share/doc/texlive-doc/latex/amsrefs/',
        ]
        # TODO find some pdfs that actually has annotations...
        annots = list(iter_annotations(roots=roots))
    assert len(annots) == 1
    assert isinstance(annots[0], Exception)


def main():
    from pprint import pprint

    logger = get_logger()
    from .common import setup_logger
    setup_logger(logger, level=logging.DEBUG)

    collected = list(annotated_pdfs())
    if len(collected) > 0:
        for r in collected:
            if isinstance(r, Exception):
                logger.exception(r)
            else:
                logger.info('collected annotations in: %s', r.path)
                for a in r.annotations:
                    pprint(a)

