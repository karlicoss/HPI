"""
Extracts data from the official Google Maps app for Android (uses gmm_sync.db for now)
"""
from __future__ import annotations

REQUIRES = [
    "protobuf",  # for parsing blobs from the database
]

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from my.core import LazyLogger, Paths, Res, datetime_aware, get_files
from my.core.common import unique_everseen
from my.core.sqlite import sqlite_connection

from ._android_protobuf import parse_labeled, parse_list, parse_place

import my.config  # isort: skip

logger = LazyLogger(__name__)


@dataclass
class config(my.config.google.maps.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


def inputs() -> Sequence[Path]:
    # TODO note sure if need to use all dbs? possibly the last one contains everything?
    return get_files(config.export_path)


PlaceId = str
ListId = str
ListName = str


@dataclass(eq=True, frozen=True)
class Location:
    lat: float
    lon: float

    @property
    def url(self) -> str:
        return f'https://maps.google.com/?q={self.lat},{self.lon}'


@dataclass(unsafe_hash=True)
class Place:
    id: PlaceId
    list_name: ListName  # TODO maybe best to keep list id?
    created_at: datetime_aware  # TODO double check it's utc?
    updated_at: datetime_aware  # TODO double check it's utc?
    title: str
    location: Location
    address: str | None
    note: str | None

    @property
    def place_url(self) -> str:
        title = quote(self.title)
        return f'https://www.google.com/maps/place/{title}/data=!4m2!3m1!1s{self.id}'

    @property
    def location_url(self) -> str:
        return self.location.url


def _process_one(f: Path):
    with sqlite_connection(f, row_factory='row') as conn:
        msg: Any

        lists: dict[ListId, ListName] = {}
        for row in conn.execute('SELECT * FROM sync_item_data WHERE corpus == 13'):  # 13 looks like lists (e.g. saved/favorited etc)
            server_id = row['server_id']

            if server_id is None:
                # this is the case for Travel plans, Followed places, Offers
                # todo alternatively could use string_index column instead maybe?
                continue

            blob = row['item_proto']
            msg = parse_list(blob)
            name = msg.f1.name
            lists[server_id] = name

        for row in conn.execute('SELECT * FROM sync_item_data WHERE corpus == 11'):  # this looks like 'Labeled' list
            ts = row['timestamp'] / 1000
            created = datetime.fromtimestamp(ts, tz=timezone.utc)

            server_id = row['server_id']
            [item_type, item_id] = server_id.split(':')
            if item_type != '3':
                # the ones that are not 3 are home/work address?
                continue

            blob = row['item_proto']
            msg = parse_labeled(blob)
            address = msg.address.full
            if address == '':
                address = None

            location = Location(lat=row['latitude_e6'] / 1e6, lon=row['longitude_e6'] / 1e6)

            yield Place(
                id=item_id,
                list_name='Labeled',
                created_at=created,
                updated_at=created,  # doesn't look like it has 'updated'?
                title=msg.title,
                location=location,
                address=address,
                note=None,  # don't think these allow notes
            )

        for row in conn.execute('SELECT * FROM sync_item_data WHERE corpus == 14'):  # this looks like actual individual places
            server_id = row['server_id']
            [list_id, _, id1, id2] = server_id.split(':')
            item_id = f'{id1}:{id2}'

            list_name = lists[list_id]

            blob = row['item_proto']
            msg = parse_place(blob)
            title = msg.f1.title
            note = msg.f1.note
            if note == '':  # seems that protobuf does that?
                note = None

            # TODO double check timezone
            created = datetime.fromtimestamp(msg.f1.created.seconds, tz=timezone.utc).replace(microsecond=msg.f1.created.nanos // 1000)

            # NOTE: this one seems to be the same as row['timestamp']
            updated = datetime.fromtimestamp(msg.f1.updated.seconds, tz=timezone.utc).replace(microsecond=msg.f1.updated.nanos // 1000)

            address = msg.f2.addr1  # NOTE: there is also addr2, but they seem identical :shrug:
            if address == '':
                address = None

            location = Location(lat=row['latitude_e6'] / 1e6, lon=row['longitude_e6'] / 1e6)

            place = Place(
                id=item_id,
                list_name=list_name,
                created_at=created,
                updated_at=updated,
                title=title,
                location=location,
                address=address,
                note=note,
            )

            # ugh. in my case it's violated by one place by about 1 second??
            # assert place.created_at <= place.updated_at
            yield place


def saved() -> Iterator[Res[Place]]:
    def it() -> Iterator[Res[Place]]:
        paths = inputs()
        total = len(paths)
        width = len(str(total))
        for idx, path in enumerate(paths):
            logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
            yield from _process_one(path)
    return unique_everseen(it)


# Summary of databases on Android (as of 20240101)
# -1_optimized_threads.notifications.db -- empty
# 1_optimized_threads.notifications.db  -- empty
# 1_tasks.notifications.db              -- empty
# -1_threads.notifications.db           -- empty
# 1_threads.notifications.db            -- doesn't look like anything interested, some trip anniversaries etc?
# 1_thread_surveys.notifications.db     -- empty
# 2_threads.notifications.db            -- empty
# accounts.notifications.db             -- just one row with account id
# brella_example_store                  -- empty
# gmm_myplaces.db                       -- contains just a few places? I think it's a subset of "Labeled"
# gmm_storage.db                        -- pretty huge, like 50Mb. I suspect it contains cache for places on maps or something
# gmm_sync.db                           -- processed above
# gnp_fcm_database                      -- list of accounts
# google_app_measurement_local.db       -- empty
# inbox_notifications.db                -- nothing interesting
# <email>_room_notifications.db         -- trip anniversaties?
# lighter_messaging_1.db                -- empty
# lighter_messaging_2.db                -- empty
# lighter_registration.db               -- empty
# peopleCache_<email>_com.google_14.db  -- contacts cache or something
# portable_geller_<email>.db            -- looks like analytics
# primes_example_store                  -- looks like analytics
# pseudonymous_room_notifications.db    -- looks like analytics
# ue3.db                                -- empty
# ugc_photos_location_data.db           -- empty
# ugc-sync.db                           -- empty
# updates-tab-visit.db                  -- empty
