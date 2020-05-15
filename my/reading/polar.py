"""
[[https://github.com/burtonator/polar-books][Polar]] articles and highlights
"""
from pathlib import Path
from typing import Type, Any, cast, TYPE_CHECKING


import my.config

if not TYPE_CHECKING:
    user_config = getattr(my.config, 'polar', None)
else:
    # mypy can't handle dynamic base classes... https://github.com/python/mypy/issues/2477
    user_config = object

# by default, Polar doesn't need any config, so perhaps makes sense to make it defensive here
if user_config is None:
    class user_config: # type: ignore[no-redef]
        pass


from dataclasses import dataclass
@dataclass
class polar(user_config):
    '''
    Polar config is optional, you only need it if you want to specify custom 'polar_dir'
    '''
    polar_dir: Path = Path('~/.polar').expanduser()


from ..core import make_config
config = make_config(polar)

# todo not sure where it keeps stuff on Windows?
# https://github.com/burtonator/polar-bookshelf/issues/296

from datetime import datetime
from typing import List, Dict, Iterable, NamedTuple, Sequence, Optional
import json

import pytz

from ..core import LazyLogger, Json
from ..core.common import isoparse
from ..error import Res, echain, sort_res_by
from ..kython.konsume import wrap, zoom, ignore, Zoomable, Wdict


logger = LazyLogger(__name__)


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



Uid = str
class Book(NamedTuple):
    uid: Uid
    created: datetime
    filename: str
    title: Optional[str]
    # TODO hmmm. I think this needs to be defensive as well...
    # think about it later.
    items: Sequence[Highlight]

Result = Res[Book]

class Loader:
    def __init__(self, p: Path) -> None:
        self.path = p
        self.uid = self.path.parent.name

    def error(self, cause: Exception, extra: str ='') -> Exception:
        if len(extra) > 0:
            extra = '\n' + extra
        return echain(Exception(f'while processing {self.path}{extra}'), cause)

    def load_item(self, meta: Zoomable) -> Iterable[Highlight]:
        meta = cast(Wdict, meta)
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
                created=isoparse(crt.value),
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
                created=isoparse(crt),
                selection=text,
                comments=tuple(comments),
            )
            h.consume()

        # TODO FIXME when I add defensive error policy, support it
        # if len(cmap) > 0:
        #     raise RuntimeError(f'Unconsumed comments: {cmap}')
        # TODO sort by date?


    def load_items(self, metas: Json) -> Iterable[Highlight]:
        for p, meta in metas.items():
            with wrap(meta, throw=False) as meta:
                yield from self.load_item(meta)

    def load(self) -> Iterable[Result]:
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
            created=isoparse(added),
            filename=filename,
            title=title,
            items=list(self.load_items(pm)),
        )


def iter_entries() -> Iterable[Result]:
    from ..core import get_files
    for d in get_files(config.polar_dir, glob='*/state.json'):
        loader = Loader(d)
        try:
            yield from loader.load()
        except Exception as ee:
            err = loader.error(ee)
            logger.exception(err)
            yield err


def get_entries() -> List[Result]:
    # sorting by first annotation is reasonable I guess???
    # todo perhaps worth making it a pattern? X() returns iterable, get_X returns reasonably sorted list?
    return list(sort_res_by(iter_entries(), key=lambda e: e.created))


def main():
    for e in iter_entries():
        if isinstance(e, Exception):
            logger.exception(e)
        else:
            logger.info('processed %s', e.uid)
            for i in e.items:
                logger.info(i)


Error = Exception # for backwards compat with Orger; can remove later
