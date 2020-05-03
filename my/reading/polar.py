"""
[[https://github.com/burtonator/polar-books][Polar]] articles and highlights
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Iterator, NamedTuple, Sequence, Optional
import json

import pytz

from ..common import LazyLogger, get_files

from ..error import Res, echain, unwrap, sort_res_by
from ..kython.konsume import wrap, zoom, ignore


_POLAR_DIR = Path('~').expanduser() / '.polar'


logger = LazyLogger(__name__)


def parse_dt(s: str) -> datetime:
    return pytz.utc.localize(datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ'))

Uid = str


# Ok I guess handling comment-level errors is a bit too much..
Cid = str
class Comment(NamedTuple):
    cid: Cid
    created: datetime
    text: str

Hid = str
class Highlight(NamedTuple):
    hid: Hid
    created: datetime
    selection: str
    comments: Sequence[Comment]


class Book(NamedTuple):
    uid: Uid
    created: datetime
    filename: str
    title: Optional[str]
    # TODO hmmm. I think this needs to be defensive as well...
    # think about it later.
    items: Sequence[Highlight]

Error = Exception # for backwards compat with Orger; can remove later

Result = Res[Book]

class Loader:
    def __init__(self, p: Path) -> None:
        self.path = p
        self.uid = self.path.parent.name

    def error(self, cause, extra='') -> Exception:
        if len(extra) > 0:
            extra = '\n' + extra
        return echain(Exception(f'while processing {self.path}{extra}'), cause)

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
                created=parse_dt(crt.value),
                text=html.value, # TODO perhaps coonvert from html to text or org?
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
                created=parse_dt(crt),
                selection=text,
                comments=tuple(comments),
            )
            h.consume()

        # TODO FIXME when I add defensive error policy, support it
        # if len(cmap) > 0:
        #     raise RuntimeError(f'Unconsumed comments: {cmap}')
        # TODO sort by date?


    def load_items(self, metas) -> Iterator[Highlight]:
        for p, meta in metas.items():
            with wrap(meta, throw=False) as meta:
                yield from self.load_item(meta)

    def load(self) -> Iterator[Result]:
        logger.info('processing %s', self.path)
        j = json.loads(self.path.read_text())

        # TODO konsume here as well?
        di = j['docInfo']
        added = di['added']
        filename = di['filename']
        title = di.get('title', None)
        tags = di['tags']
        pm = j['pageMetas']

        yield Book(
            uid=self.uid,
            created=parse_dt(added),
            filename=filename,
            title=title,
            items=list(self.load_items(pm)),
        )


def iter_entries() -> Iterator[Result]:
    for d in get_files(_POLAR_DIR, glob='*/state.json'):
        loader = Loader(d)
        try:
            yield from loader.load()
        except Exception as ee:
            err = loader.error(ee)
            logger.exception(err)
            yield err


def get_entries() -> List[Result]:
    # sorting by first annotation is reasonable I guess???
    return list(sort_res_by(iter_entries(), key=lambda e: e.created))


def main():
    for entry in iter_entries():
        try:
            ee = unwrap(entry)
        except Error as e:
            logger.exception(e)
        else:
            logger.info('processed %s', ee.uid)
            for i in ee.items:
                logger.info(i)
