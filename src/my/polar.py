"""
[[https://github.com/burtonator/polar-bookshelf][Polar]] articles and highlights

The `polar` config section is optional when your library is in `~/.polar`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, cast

from my.core import Json, Res, datetime_aware, get_files, make_logger
from my.core.error import sort_res_by
from my.core.konsume import Wdict, Zoomable, wrap

logger = make_logger(__name__)


class Config:
    @property
    def polar_dir(self) -> Path | str:
        """Directory containing the Polar library (defaults to ~/.polar)."""
        # TODO check the default location on Windows.
        # https://github.com/burtonator/polar-bookshelf/issues/296
        return Path.home() / '.polar'

    @property
    def defensive(self) -> bool:
        """Set to False to report unconsumed fields when debugging (defaults to True)."""
        return True


def make_config() -> Config:
    import my.config

    if getattr(my.config, 'polar', None) is None:
        return Config()

    class combined_config(my.config.polar, Config):
        pass

    return combined_config()


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
    def __init__(self, p: Path, *, config: Config | None = None) -> None:
        self.path = p
        self.uid = self.path.parent.name
        self.config = make_config() if config is None else config

    def load_item(self, meta: Zoomable) -> Iterable[Highlight]:
        meta = cast(Wdict, meta)
        # TODO this should be destructive zoom?
        meta['notes'].zoom()  # TODO what goes in 'notes' when it isn't empty?

        meta['pagemarks'].consume_all()

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
        for v in comments:
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
                created=datetime.fromisoformat(crt.value),
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
                created=datetime.fromisoformat(crt),
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
        for meta in metas.values():
            with wrap(meta, throw=not self.config.defensive) as meta:
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

        path = Path(self.config.polar_dir) / 'stash' / filename

        yield Book(
            created=datetime.fromisoformat(added),
            uid=self.uid,
            path=path,
            title=title,
            items=list(self.load_items(pm)),
            tags=tags,
        )


def iter_entries() -> Iterable[Result]:
    config = make_config()
    for d in get_files(config.polar_dir, glob='*/state.json'):
        loader = Loader(d, config=config)
        try:
            yield from loader.load()
        except Exception as e:
            e.add_note(f'^ while processing {d}')
            yield e


def get_entries() -> list[Result]:
    # sorting by first annotation is reasonable I guess???
    # todo perhaps worth making it a pattern? X() returns iterable, get_X returns reasonably sorted list?
    return sort_res_by(iter_entries(), key=lambda e: e.created)
