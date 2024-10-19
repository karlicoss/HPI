'''
PDF documents and annotations on your filesystem
'''
from __future__ import annotations as _annotations

REQUIRES = [
    'git+https://github.com/0xabu/pdfannots',
    # todo not sure if should use pypi version?
]

import time
from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Optional, Protocol

import pdfannots
from more_itertools import bucket

from my.core import PathIsh, Paths, Stats, get_files, make_logger, stat
from my.core.cachew import mcachew
from my.core.error import Res, split_errors


class config(Protocol):
    @property
    def paths(self) -> Paths:
        return ()  # allowed to be empty for 'filelist' logic

    def is_ignored(self, p: Path) -> bool:  # noqa: ARG002
        """
        You can override this in user config if you want to ignore some files that are tooheavy
        """
        return False


def make_config() -> config:
    from my.config import pdfs as user_config

    class migration:
        @property
        def paths(self) -> Paths:
            roots = getattr(user_config, 'roots', None)
            if roots is not None:
                from my.core.warnings import high

                high('"roots" is deprecated! Use "paths" instead.')
                return roots
            else:
                return ()

    class combined_config(user_config, migration, config): ...

    return combined_config()


logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    cfg = make_config()
    all_files = get_files(cfg.paths, glob='**/*.pdf')
    return [p for p in all_files if not cfg.is_ignored(p)]


# TODO canonical names/fingerprinting?
# TODO defensive if pdf was removed, also cachew key needs to be defensive
class Annotation(NamedTuple):
    path: str
    author: Optional[str]
    page: int
    highlight: Optional[str]
    comment: Optional[str]
    created: Optional[datetime]  # note: can be tz unaware in some bad pdfs...

    @property
    def date(self) -> datetime | None:
        # legacy name
        return self.created


def _as_annotation(*, raw: pdfannots.Annotation, path: str) -> Annotation:
    d = vars(raw)
    pos = raw.pos
    # make mypy happy (pos always present for Annotation https://github.com/0xabu/pdfannots/blob/dbdfefa158971e1746fae2da139918e9f59439ea/pdfannots/types.py#L302)
    assert pos is not None
    d['page'] = pos.page.pageno
    return Annotation(
        path      = path,
        author    = d['author'],
        page      = d['page'],
        highlight = raw.gettext(),
        comment   = d['contents'],
        created   = d['created'],
    )


def get_annots(p: Path) -> list[Annotation]:
    b = time.time()
    with p.open('rb') as fo:
        doc = pdfannots.process_file(fo, emit_progress_to=None)
        annots = list(doc.iter_annots())
        # also has outlines are kinda like TOC, I don't really need them
    a = time.time()
    took = a - b
    tooks = f'took {took:0.1f} seconds'
    if took > 5:
        tooks = tooks.upper()
    logger.debug('extracting %s %s: %d annotations', tooks, p, len(annots))
    return [_as_annotation(raw=a, path=str(p)) for a in annots]


def _hash_files(pdfs: Sequence[Path]):
    # if mtime hasn't changed then the file hasn't changed either
    return [(pdf, pdf.stat().st_mtime) for pdf in pdfs]


# TODO might make more sense to be more fine grained here, e.g. cache annotations for indifidual files
@mcachew(depends_on=_hash_files)
def _iter_annotations(pdfs: Sequence[Path]) -> Iterator[Res[Annotation]]:
    logger.info('processing %d pdfs', len(pdfs))

    # todo how to print to stdout synchronously?
    # todo global config option not to use pools? useful for debugging..
    from concurrent.futures import ProcessPoolExecutor

    from my.core.utils.concurrent import DummyExecutor

    workers = None  # use 0 for debugging
    Pool = DummyExecutor if workers == 0 else ProcessPoolExecutor
    with Pool(workers) as pool:
        futures = [pool.submit(get_annots, pdf) for pdf in pdfs]
        for f, pdf in zip(futures, pdfs):
            try:
                yield from f.result()
            except Exception as e:
                logger.error('While processing %s:', pdf)
                logger.exception(e)
                # todo add a comment that it can be ignored... or something like that
                # TODO not sure if should attach pdf as well; it's a bit annoying to pass around?
                # also really have to think about interaction with cachew...
                yield e


def annotations() -> Iterator[Res[Annotation]]:
    pdfs = inputs()
    yield from _iter_annotations(pdfs=pdfs)


class Pdf(NamedTuple):
    path: Path
    annotations: Sequence[Annotation]

    @property
    def created(self) -> datetime | None:
        annots = self.annotations
        return None if len(annots) == 0 else annots[-1].created

    @property
    def date(self) -> datetime | None:
        # legacy
        return self.created


def annotated_pdfs(*, filelist: Sequence[PathIsh] | None = None) -> Iterator[Res[Pdf]]:
    if filelist is not None:
        # hacky... keeping it backwards compatible
        # https://github.com/karlicoss/HPI/pull/74
        from my.config import pdfs as user_config

        user_config.paths = filelist
    ait = annotations()
    vit, eit = split_errors(ait, ET=Exception)

    bucketed = bucket(vit, key=lambda a: a.path)
    for k in bucketed:
        g = list(bucketed[k])
        yield Pdf(path=Path(k), annotations=g)
    yield from eit


def stats() -> Stats:
    return {
        **stat(annotations),
        **stat(annotated_pdfs),
    }


### legacy/misc stuff
if not TYPE_CHECKING:
    iter_annotations = annotations
###
