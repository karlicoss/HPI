'''
Data from Podcast Addict Android app (https://podcastaddict.com/app)
'''

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path
from typing import Protocol

from my.core import Paths, get_files, make_logger
from my.core.compat import KW_ONLY
from my.core.sqlite import sqlite_connection

from ._utils import DbRow, MultiKeyTracker, dict_diff

logger = make_logger(__name__)


class Config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """
        Path/glob[s] to sqlite app database (/data/data/com.bambuna.podcastaddict/databases/podcastAddict.db)
        """
        raise NotImplementedError


# FIXME rename to 'default config'? not sure, might be a bit confusing..
def make_config() -> Config:
    from my.config import podcastaddict as user_config

    class combined_config(user_config.android, Config): ...

    return combined_config()


# todo how to keep consistent with Status class?
_IS_EPISODE_INTERESTING = '''
/* not sure what is this.. perhaps file accidentally opened via podcastaddict? */
episodes.podcast_id >= 0
AND
(
episodes.favorite != 0
OR
episodes.seen_status != 0
OR
episodes.position_to_resume != 0
OR
/* NOTE: might have playbackDate != -1, but position_to_resume etc == 0 */
episodes.playbackDate != -1
)
'''

_EPISODES_QUERY = f'''
SELECT episodes.*, podcasts.name AS podcast_name
FROM episodes JOIN podcasts ON episodes.podcast_id == podcasts._id
WHERE {_IS_EPISODE_INTERESTING}
ORDER BY guid
'''

# just to 'normalize' data, remove volatile/useless fields
_VOLATILE_AND_USELESS_COLUMNS = [
    'rssfeed_duration_ms',
    'thumbnail_id',
    'chapters_extracted',
    'downloaded_status',
    'downloaded_date',
    'downloaded_status_int',
    'local_file_name',
    'donation_url',
    'explicit',
    'iTunesType',
    'seasonNb',
    'episodeNb',
    'seasonName',
    'thumbsRating',
    'alternate_urls',
    'size',

    '_id',  # can change if you reset phone or something??

    'creator',  # we rely on podcast.name anyway
    'server_id',  # can change to -1? not sure what it means

    # weird.. sometimes it changes slightly?
    # seems like better to rely on duration_ms anyway, it's not changing
    'duration',

    'download_url',  # probs not super useful, can just use podcast page url
]  # fmt: skip


# these don't look volatile but also perhaps not much use?
# for now we don't do anything about them
# todo perhaps might be useful for bleanser?
_USELESS_COLUMNS = [
    'podcast_id',
    'comments',
    'thumbnail_url',
    'comment_rss',
    'type',
    'new_status',
    'deleted_status',
    'comments_last_modified',
    'comments_etag',
    'flattr',
    'is_virtual',
    'is_artwork_extracted',
    'virtualPodcastName',
    'normalizedType',
    'hasBeenFlattred',
    'download_error_msg',
    'media_extracted_artwork_id',
    'automatically_shared',
    'transcript_url',
    'chapters_url',
]


@dataclass(**KW_ONLY)
class Podcast:
    row: DbRow

    @property
    def name(self) -> str:
        return self.row['name']

    @property
    def homepage(self) -> str | None:
        return self.row['homepage']

    @property
    def subscribed(self) -> bool:
        return self.row['subscribed_status'] > 0

    @property
    def description_html(self) -> str:
        return self.row['description']


_STATUS_COLUMNS = [
    'playbackDate',
    'position_to_resume',
    'seen_status',
]


@dataclass(**KW_ONLY)
class Status:
    # note: there is also 'playing_status' column, but it seems to be always 0
    row: DbRow

    @property
    def playback_dt(self) -> datetime | None:
        """
        Usually playbackDate is changing when there are other status changes... however not always!
        todo perhaps could take from timestamp/file name? not sure
        """
        pb = self.row.get('playbackDate')
        if pb is None:
            return None
        if pb == -1:
            # todo might be nice to tell apart from None case?
            return None
        return datetime.fromtimestamp(pb / 1000, tz=timezone.utc)

    @property
    def position_to_resume(self) -> int | None:
        return self.row.get('position_to_resume')

    @property
    def seen(self) -> bool | None:
        s = self.row.get('seen_status')
        if s is None:
            return None
        return s == 1


@dataclass(**KW_ONLY)
class Episode:
    row: DbRow
    statuses: list[Status]
    podcast: Podcast

    @property
    def guid(self) -> str:
        return self.row['guid']

    @property
    def name(self) -> str:
        return self.row['name']

    @property
    def url(self) -> str | None:
        return self.row['url']

    @property
    def publication_dt(self) -> datetime:
        # todo not 100% sure if it's UTC?
        # tricky to find out for sure, the app doesn't show podcast publication time..
        return datetime.fromtimestamp(self.row['publication_date'] / 1000, tz=timezone.utc)

    @property
    def short_description(self) -> str:
        # NOTE: # there is also
        # - description column, but it seems to be always empty
        # - content column, but it's HTML, but it can be NULL and quite long.. so not using for now
        # - short_description seems to be always present and contain something meaningful
        return self.row['short_description']

    @property
    def duration_ms(self) -> int:
        # NOTE: there is also 'duration' column (hh:mm:ss string), but seems like it's volatile?
        # so we filter it out
        return self.row['duration_ms']


class Processor:
    def __init__(self, *, config: Config) -> None:
        self.config = config

    # NOTE: putting inputs as a separate method might make it friendlier for hpi stat etc to discover?
    def inputs(self) -> Sequence[Path]:
        return get_files(self.config.export_path)

    def _db_rows(self) -> Iterator[tuple[Iterable[DbRow], Iterable[DbRow]]]:
        db_files = self.inputs()
        total = len(db_files)
        width = len(str(total))

        # NOTE: atm we're not doing any row deduplication between different dbs
        # it doesn't really make much performance difference with all the weird podcast processing

        for idx, db_file in enumerate(db_files):
            logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {db_file}')
            with sqlite_connection(db_file, immutable=True, row_factory='dict') as db:
                db_podcast_id_to_podcast: dict[int, DbRow] = {}
                for row in db.execute('SELECT * FROM podcasts WHERE _id > 0'):
                    db_podcast_id = row.pop('_id')
                    db_podcast_id_to_podcast[db_podcast_id] = row

                episodes_rows: list[DbRow] = []
                for row in db.execute(_EPISODES_QUERY):
                    # remove volatile columns for unique_everseen to work properly down the line
                    # TODO can we do it via sqlite instead?
                    row = {k: v for k, v in row.items() if k not in set(_VOLATILE_AND_USELESS_COLUMNS)}

                    # remove podcast_id since it only makes sense within a single db, so we don't use it by accident
                    db_podcast_id = row.pop('podcast_id')
                    row['podcast'] = db_podcast_id_to_podcast[db_podcast_id]
                    # remove podcast name as well, to avoid volatility in Episode objects
                    # we have reference to podcast object anyway
                    row.pop('podcast_name', None)

                    episodes_rows.append(row)

                podcasts_rows = db_podcast_id_to_podcast.values()
                yield (podcasts_rows, episodes_rows)

    def data(self) -> Iterator[Podcast | Episode]:
        # need to keep track of all podcasts ever emitted before, so we can correctly set is_subscribed attribute
        def podcast_meta_updater(current: DbRow, new: DbRow) -> None:
            # ugh. sometimes homepage disappears for no reason??
            nh = new['homepage']
            if nh is None:
                # just remove it from updates in this case, so original homepage is preserved
                new.pop('homepage', None)
            current.update(new)

        podcasts_tracker = MultiKeyTracker(
            keys=[
                # if any of the keys match, the podcasts are the same
                ('server_id', -1),
                ('iTunesID', ''),
                ('feed_url', None),
                ('name', ''),
            ],
            updater=podcast_meta_updater,
        )

        # maps from episode guid
        all_episodes: dict[str, Episode] = {}

        for podcast_rows, episodes_rows in self._db_rows():
            ###
            # we want to recover the exact object that we keep so we can apply updates
            # so this map is from object id() function
            podcasts_in_current_db: dict[int, DbRow] = {}

            # first process (and emit if necessary interesting podcast object)
            # - ones that we're subscribed to
            # - oncs that we listened to (via episodes)
            for prow in chain(
                (prow for prow in podcast_rows if prow['subscribed_status'] > 0),
                (erow['podcast'] for erow in episodes_rows),
            ):
                prev = podcasts_tracker.set(prow, add=True, update=True)
                if prev is not None:
                    # only updated existing item
                    podcasts_in_current_db[id(prev)] = prev
                else:
                    # prow is the newly inserted item
                    podcasts_in_current_db[id(prow)] = prow
                    # FIXME need to update actual podcast object.. it shouldn't change
                    # for now it's ok, we're keeping dict reference anyway
                    yield Podcast(row=prow)

            for prow in podcast_rows:
                prev = podcasts_tracker.set(prow, add=False, update=True)
                if prev is not None:
                    podcasts_in_current_db[id(prev)] = prev

            # FIXME need to be careful with cachew...
            # i.e. we might update row after it's been cached??
            for _k, v in podcasts_tracker.items:
                if id(v) not in podcasts_in_current_db:
                    # if it's not in the db anymore, we've likely unsubscribed
                    v['subscribed_status'] = 0
            ###

            for erow in episodes_rows:
                row = erow
                guid = row['guid']

                ep = all_episodes.get(guid)
                if ep is None:
                    status = Status(row={k: row[k] for k in _STATUS_COLUMNS})
                    podcast_dict = row['podcast']
                    podcast_dict = podcasts_tracker.get(podcast_dict)
                    ep = Episode(
                        row=row,
                        statuses=[status],
                        podcast=Podcast(row=podcast_dict),  # todo make sure to refer to the same Podcast object...
                    )
                    all_episodes[guid] = ep
                    yield ep
                    continue

                # otherwise try to update the object/compute statuses
                prev_row = ep.row
                diff = dict_diff(prev_row, row)

                # TODO hmm
                # maybe it's better to 'normalise' data and split out status update fields from podcast rows?
                # after that emitting diffs etc might be simpler?

                # TODO maybe update all of them? idk if there is much point trying to tell it apart...
                for key in [
                    'url',  # often legitimately updates, best to use the latest one
                    'content',  # changes often
                    'duration_ms',  # only one instance of it changing (by 1ms??) but whatever
                    'categories',  # had one instance where it changed to None?? but whatever
                ]:
                    key_changes = diff.get(key)
                    if key_changes is None:
                        continue
                    (_prev_value, new_value) = key_changes
                    if new_value is not None:
                        # do not overwrite if new value is None
                        prev_row[key] = new_value
                    del diff[key]

                if len(diff) == 0:
                    continue

                # TODO check if there are any other unexpected diffs not in Status?
                status_dict = {key: new_value for (key, (_prev_value, new_value)) in diff.items()}
                prev_row.update(status_dict)
                status = Status(row=status_dict)
                ep.statuses.append(status)


# TODO how to make it hpi stat friendly?
# can still extract typing annotations etc, but I guess need to decide on some sort of convention?...
def processor() -> Processor:
    return Processor(config=make_config())
