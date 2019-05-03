#!/usr/bin/python3
from pathlib import Path
import logging
from typing import List, Dict, Iterator, NamedTuple, Sequence, Optional
import json

from kython.kerror import ResT, echain, unwrap, sort_res_by
from kython.klogging import setup_logzero


BDIR = Path('/L/zzz_syncthing/data/.polar')


def get_logger():
    return logging.getLogger('polar-provider')


def _get_datas() -> List[Path]:
    return list(sorted(BDIR.glob('*/state.json')))


Uid = str

class Error(Exception):
    def __init__(self, p: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs) # type: ignore
        self.uid: Uid = p.parent.name

ResultItem = ResT['Item', Error]
class Item(NamedTuple):
    uid: Uid

ResultBook = ResT['Book', Error]

class Book(NamedTuple):
    uid: Uid
    filename: str
    title: Optional[str]
    items: Sequence[ResultItem]

from kython.konsume import zoom, akeq

class Loader:
    def __init__(self, p: Path) -> None:
        self.path = p
        self.uid = self.path.parent.name
        self.err = Error(p)
        self.logger = get_logger()

    def error(self, cause, extra):
        return echain(Error(self.path, extra), cause)

    def load_item(self, meta) -> Iterator[ResultItem]:
        # TODO this should be destructive zoom?
        try:
            meta['notes'].zoom()
            meta['pagemarks'].zoom()
            if 'notes' in meta:
                # TODO something nicer?
                notes = meta['notes'].zoom()
            else:
                notes = [] # TODO FIXME dict?
            comments = meta['comments'].zoom()
            meta['questions'].zoom()
            meta['flashcards'].zoom()
            highlights = meta['textHighlights'].zoom()
            meta['areaHighlights'].zoom()
            meta['screenshots'].zoom()
            meta['thumbnails'].zoom()
            if 'readingProgress' in meta:
                meta['readingProgress'].zoom()

            # TODO want to ignore the whold subtree..
            pi = meta['pageInfo'].zoom()
            pi['num'].zoom()
        except Exception as exx:
            err = self.error(exx, meta)
            self.logger.exception(err)
            yield err
            return # TODO ugh, careful with unconsumed?

        # TODO how to make it nicer?
        vals = list(comments.values())
        for v in vals:
            cid = v['id'].zoom()
            v['guid'].zoom()
            # TODO values should probably be checked by flow analysis??
            crt = v['created'].zoom()
            updated = v['lastUpdated'].zoom()
            content = v['content'].zoom()
            html = content['HTML'].zoom()
            v['ref'].zoom()
            v.consume()

        highlights.consume_all() # TODO FIXME
        # TODO need to process text highlights...


    def load_items(self, metas) -> Iterator[ResultItem]:
        from kython.konsume import wrap
        for p, meta in metas.items():
            with wrap(meta) as meta:
                yield from self.load_item(meta)

    def load(self) -> Iterator[ResultBook]:
        self.logger.info('processing %s', self.path)
        j = json.loads(self.path.read_text())

        try:
            di = j['docInfo']
            filename = di['filename']
            title = di.get('title', None)
            tags = di['tags']
            pm = j['pageMetas']
        except Exception as ex:
            err = self.error(ex, j)
            self.logger.exception(err)
            yield err
            return

        # TODO should I group by book??? 
        yield Book(
            uid=self.uid,
            filename=filename,
            title=title,
            items=list(self.load_items(pm)),
        )
        # "textHighlights": {},
        # "comments": {},
        # TODO
        # "pagemarks": {},
        # "notes": {},
        # "questions": {},
        # "flashcards": {},
        # "areaHighlights": {},
        # "screenshots": {},
        # "thumbnails": {},
        # "readingProgress": {},
        # "pageInfo": {
        #   "num": 1
        # }


def iter_entries() -> Iterator[ResultBook]:
    for d in _get_datas():
        yield from Loader(d).load()


def main():
    logger = get_logger()
    setup_logzero(logger, level=logging.DEBUG)

    for entry in iter_entries():
        logger.info('processed %s', entry.uid)
        for i in entry.items:
            try:
                ii = unwrap(i)
            except Error as e:
                logger.exception(e)
            else:
                logger.info(ii)


if __name__ == '__main__':
    main()
