"""
[[https://github.com/burtonator/polar-bookshelf][Polar]] articles and highlights
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, cast

from my.core import (
    Json,
    PathIsh,
    Res,
    datetime_aware,
    get_files,
    make_config,
    make_logger,
)
from my.core.compat import add_note, fromisoformat
from my.core.error import sort_res_by
from my.core.konsume import Wdict, Zoomable, wrap

import my.config  # isort: skip

logger = make_logger(__name__)


# todo use something similar to tz.via_location for config fallback
if not TYPE_CHECKING:
    user_config = getattr(my.config, 'polar', None)
else:
    # mypy can't handle dynamic base classes... https://github.com/python/mypy/issues/2477
    user_config = object

# by default, Polar doesn't need any config, so perhaps makes sense to make it defensive here
if user_config is None:

    class user_config:  # type: ignore[no-redef]
        pass


@dataclass
class polar(user_config):
    '''
    Polar config is optional, you only need it if you want to specify custom 'polar_dir'
    '''

    polar_dir: PathIsh = Path('~/.polar').expanduser()  # noqa: RUF009
    defensive: bool = True  # pass False if you want it to fail faster on errors (useful for debugging)


config = make_config(polar)

# todo not sure where it keeps stuff on Windows?
# https://github.com/burtonator/polar-bookshelf/issues/296


# Ok I guess handling comment-level errors is a bit too much..
Cid = str


class Comment(NamedTuple):
    cid: Cid
    created: datetime_aware
    text: str


Hid = str


class Highlight(NamedTuple):
    hid: Hid
    created: datetime_aware
    selection: str
    comments: Sequence[Comment]
    tags: Sequence[str]
    page: int  # 1-indexed
    color: str | None = None


Uid = str


class Book(NamedTuple):
    created: datetime_aware
    uid: Uid
    path: Path
    title: str | None
    # TODO hmmm. I think this needs to be defensive as well...
    # think about it later.
    items: Sequence[Highlight]

    tags: Sequence[str]

    @property
    def filename(self) -> str:
        # TODO deprecate
        return str(self.path)


Result = Res[Book]


class Loader:
    def __init__(self, p: Path) -> None:
        self.path = p
        self.uid = self.path.parent.name

    def load_item(self, meta: Zoomable) -> Iterable[Highlight]:
        meta = cast(Wdict, meta)
        # TODO this should be destructive zoom?
        meta['notes'].zoom()  # TODO ??? is it deliberate?

        meta['pagemarks'].consume_all()

        if 'notes' in meta:
            # TODO something nicer?
            _notes = meta['notes'].zoom()
        else:
            _notes = []
        # not sure what is 'notes', seemed always empty for me?

        comments = list(meta['comments'].zoom().values()) if 'comments' in meta else []
        meta['questions'].zoom()
        meta['flashcards'].zoom()
        highlights = meta['textHighlights'].zoom()

        # TODO could be useful to at least add a meta bout area highlights/screens
        meta['areaHighlights'].consume_all()
        meta['screenshots'].zoom()
        meta['thumbnails'].zoom()
        if 'readingProgress' in meta:
            meta['readingProgress'].consume_all()

        # TODO want to ignore the whole subtree..
        pi = meta['pageInfo'].zoom()
        page = pi['num'].zoom().value
        if 'dimensions' in pi:
            pi['dimensions'].consume_all()

        # TODO how to make it nicer?
        cmap: dict[Hid, list[Comment]] = {}
        vals = list(comments)
        for v in vals:
            cid = v['id'].zoom()
            v['guid'].zoom()
            # TODO values should probably be checked by flow analysis??
            crt = v['created'].zoom()
            _updated = v['lastUpdated'].zoom()
            content = v['content'].zoom()
            html = content['HTML'].zoom()
            refv = v['ref'].zoom().value
            [_, hlid] = refv.split(':')
            ccs = cmap.get(hlid, [])
            cmap[hlid] = ccs
            comment = Comment(
                cid=cid.value,
                created=fromisoformat(crt.value),
                text=html.value,  # TODO perhaps coonvert from html to text or org?
            )
            ccs.append(comment)
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
            _updated = h['lastUpdated'].zoom().value
            h['rects'].ignore()

            # TODO make it more generic..
            htags: list[str] = []
            if 'tags' in h:
                ht = h['tags'].zoom()
                for _k, v in list(ht.items()):
                    ctag = v.zoom()
                    ctag['id'].consume()
                    ct = ctag['label'].zoom()
                    htags.append(ct.value)

            h['textSelections'].ignore()
            h['notes'].consume()
            h['questions'].consume()
            h['flashcards'].consume()
            color = h['color'].zoom().value
            h['images'].ignore()
            # TODO eh, quite excessive \ns...
            text = h['text'].zoom()['TEXT'].zoom().value

            yield Highlight(
                hid=hid,
                created=fromisoformat(crt),
                selection=text,
                comments=tuple(comments),
                tags=tuple(htags),
                page=page,
                color=color,
            )
            h.consume()

        # TODO when I add defensive error policy, support it
        # if len(cmap) > 0:
        #     raise RuntimeError(f'Unconsumed comments: {cmap}')
        # TODO sort by date?

    def load_items(self, metas: Json) -> Iterable[Highlight]:
        for _p, meta in metas.items():  # noqa: PERF102
            with wrap(meta, throw=not config.defensive) as meta:
                yield from self.load_item(meta)

    def load(self) -> Iterable[Result]:
        logger.info('processing %s', self.path)
        j = json.loads(self.path.read_text())

        # TODO konsume here as well?
        di = j['docInfo']
        added = di['added']
        filename = di['filename']
        title = di.get('title', None)
        tags_dict = di['tags']
        pm = j['pageMetas']  # todo handle this too?

        # todo defensive?
        tags = tuple(t['label'] for t in tags_dict.values())

        path = Path(config.polar_dir) / 'stash' / filename

        yield Book(
            created=fromisoformat(added),
            uid=self.uid,
            path=path,
            title=title,
            items=list(self.load_items(pm)),
            tags=tags,
        )


def iter_entries() -> Iterable[Result]:
    for d in get_files(config.polar_dir, glob='*/state.json'):
        loader = Loader(d)
        try:
            yield from loader.load()
        except Exception as e:
            add_note(e, f'^ while processing {d}')
            yield e


def get_entries() -> list[Result]:
    # sorting by first annotation is reasonable I guess???
    # todo perhaps worth making it a pattern? X() returns iterable, get_X returns reasonably sorted list?
    return list(sort_res_by(iter_entries(), key=lambda e: e.created))


## deprecated
if not TYPE_CHECKING:
    # "deprecate" by hiding from mypy
    Error = Exception  # for backwards compat with Orger; can remove later
