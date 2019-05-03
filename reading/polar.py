#!/usr/bin/python3
from pathlib import Path
import logging
from typing import List, Dict, Iterator, NamedTuple, Sequence, Optional
import json

from kython.kerror import ResT, echain, unwrap, sort_res_by
from kython.klogging import setup_logzero
from kython.konsume import wrap, zoom, ignore


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

# TODO not sure if I even need comment?
# Ok I guess handling comment-level errors is a bit too much..

Cid = str
class Comment(NamedTuple):
    cid: Cid
    created: str # TODO datetime (parse iso)
    comment: str

Hid = str
class Highlight(NamedTuple):
    hid: Hid
    created: str # TODO datetime
    selection: str
    comments: Sequence[Comment]



ResultBook = ResT['Book', Error]

class Book(NamedTuple):
    uid: Uid
    filename: str
    title: Optional[str]
    items: Sequence[Highlight]


class Loader:
    def __init__(self, p: Path) -> None:
        self.path = p
        self.uid = self.path.parent.name
        self.err = Error(p)
        self.logger = get_logger()

    def error(self, cause, extra):
        return echain(Error(self.path, extra), cause)

    def load_item(self, meta) -> Iterator[Highlight]:
        # TODO this should be destructive zoom?
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

        # TODO how to make it nicer?
        cmap: Dict[Hid, List[Comment]] = {}
        vals = list(comments.values())
        for v in vals:
            cid = v['id'].zoom()
            v['guid'].zoom()
            # TODO values should probably be checked by flow analysis??
            crt = v['created'].zoom()
            updated = v['lastUpdated'].zoom()
            content = v['content'].zoom()
            html = content['HTML'].zoom()
            refv = v['ref'].zoom().value
            [_, hlid] = refv.split(':')
            ccs = cmap.get(hlid, [])
            cmap[hlid] = ccs
            ccs.append(Comment(
                cid=cid.value,
                created=crt.value,
                comment=html.value, # TODO perhaps coonvert from html to text or org?
            ))
            v.consume()
        for h in list(highlights.values()):
            hid = h['id'].zoom().value
            if hid in cmap:
                comments = cmap[hid]
                del cmap[hid]
            else:
                comments = []

            h['guid'].consume()
            crt = h['created'].zoom().value
            updated = h['lastUpdated'].zoom().value
            h['rects'].ignore()

            h['textSelections'].ignore()
            h['notes'].consume()
            h['questions'].consume()
            h['flashcards'].consume()
            h['color'].consume()
            h['images'].ignore()
            # TODO eh, quite excessive \ns...
            text = h['text'].zoom()['TEXT'].zoom().value

            yield Highlight(
                hid=hid,
                created=crt,
                selection=text,
                comments=tuple(comments),
            )
            h.consume()

        if len(cmap) > 0:
            raise RuntimeError(f'Unconsumed comments: {cmap}')
        # TODO sort by date?


    def load_items(self, metas) -> Iterator[Highlight]:
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
        try:
            ee = unwrap(entry)
        except Error as e:
            logger.exception(e)
        else:
            for i in ee.items:
                logger.info(i)


if __name__ == '__main__':
    main()
