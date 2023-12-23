"""
Data from offficial app for Android
"""
import re
from struct import unpack_from, calcsize

from my.core.sqlite import sqlite_connect_immutable


def _parse_content(data: bytes):
    pos = 0

    def skip(count: int) -> None:
        nonlocal pos
        pos += count

    def getstring(slen: int) -> str:
        if slen == 1:
            lfmt = '>B'
        elif slen == 2:
            lfmt = '>H'
        else:
            raise RuntimeError

        (sz,) = unpack_from(lfmt, data, offset=pos)
        skip(slen)
        assert sz > 0
        assert sz <= 10000  # sanity check?

        # soo, this is how it should ideally work:
        # (ss,) = unpack_from(f'{sz}s', data, offset=pos)
        # skip(sz)
        # however sometimes there is a discrepancy between string length in header and actual length (if you stare at the data)
        # example is 1725868458246570412
        # wtf??? (see logging below)

        # ughhhh
        seps = [
            b'I\x08',
            b'I\x09',
        ]
        sep_idxs = [data[pos:].find(sep) for sep in seps]
        sep_idxs = [i for i in sep_idxs if i != -1]
        assert len(sep_idxs) > 0
        sep_idx = min(sep_idxs)

        # print("EXPECTED LEN", sz, "GOT", sep_idx, "DIFF", sep_idx - sz)

        zz = data[pos : pos + sep_idx]
        skip(sep_idx)
        return zz.decode('utf8')

    skip(2)  # always starts with 4a03?

    (xx,) = unpack_from('B', data, offset=pos)
    skip(1)
    # print("TYPE:", xx)

    # wtf is this... maybe it's a bitmask?
    slen = {
        66 : 1,
        67 : 2,
        106: 1,
        107: 2,
    }[xx]

    text = getstring(slen=slen)

    # after the main tweet text it contains entities (e.g. shortened urls)
    # however couldn't reverse engineer the schema properly, the links are kinda all over the place

    # TODO this also contains image alt descriptions?
    # see 1665029077034565633

    extracted = []
    linksep = 0x6a
    while True:
        m = re.search(b'\x6a.http', data[pos:])
        if m is None:
            break

        qq = m.start()
        pos += qq

        while True:
            if data[pos] != linksep:
                break
            pos += 1
            (sz,) = unpack_from('B', data, offset=pos)
            pos += 1
            (ss,) = unpack_from(f'{sz}s', data, offset=pos)
            pos += sz
            extracted.append(ss)

    replacements = {}
    i = 0
    while i < len(extracted):
        if b'https://t.co/' in extracted[i]:
            key = extracted[i].decode('utf8')
            value = extracted[i + 1].decode('utf8')
            i += 2
            replacements[key] = value
        else:
            i += 1

    for k, v in replacements.items():
        text = text.replace(k, v)
    assert 'https://t.co/' not in text  # make sure we detected all links

    print(text)



PATH_TO_DB = '/path/to/db'


with sqlite_connect_immutable(PATH_TO_DB) as db:
    # TODO use statuses table instead?
    # has r_ent_content??
    # TODO hmm r_ent_content contains expanded urls?
    # but they are still ellipsized? e.g. you can check 1692905005479580039
    # TODO also I think content table has mappings from short urls to full, need to extract
    for (tid, blob, blob2) in db.execute(
        f'SELECT statuses_status_id, CAST(statuses_content AS BLOB), CAST(statuses_r_ent_content AS BLOB) FROM timeline_view WHERE statuses_bookmarked = 1',
    ):
        if blob is None:  # TODO exclude in sql query?
            continue
        print("----")
        try:
            print("PARSING", tid)
            _parse_content(blob)
            # _parse_content(blob2)
        except UnicodeDecodeError as ue:
            raise ue
            # print("DECODING ERROR FOR ", tid, ue.object)
