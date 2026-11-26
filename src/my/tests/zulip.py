import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from my.core import unwrap
from my.core.cfg import tmp_config
from my.zulip import organization


def _zulip_archive(path: Path) -> Path:
    realm = {
        'zerver_realm': [{'id': 1, 'string_id': 'example', 'name': 'Example Org'}],
        'zerver_userprofile': [{'id': 10, 'full_name': 'Alice', 'email': 'alice@example.com'}],
        'zerver_userprofile_crossrealm': [],
    }
    messages = {
        'zerver_message': [
            {
                'id': 42,
                'date_sent': 1_700_000_000,
                'subject': 'greetings',
                'sender': 10,
                'content': 'hello world',
            },
        ],
    }

    with tarfile.open(path, 'w:gz') as tf:
        dir_info = tarfile.TarInfo('zulip-export-1')
        dir_info.type = tarfile.DIRTYPE
        tf.addfile(dir_info)
        for relpath, payload in (
            ('zulip-export-1/realm.json', realm),
            ('zulip-export-1/messages-000001.json', messages),
        ):
            data = json.dumps(payload).encode()
            info = tarfile.TarInfo(relpath)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return path


def test_zulip_organization_targz(tmp_path: Path) -> None:
    archive = _zulip_archive(tmp_path / 'zulip-export-1.tar.gz')

    class zulip:
        class organization:
            export_path = archive

    with tmp_config() as cfg:
        cfg.zulip = zulip
        [msg] = organization.messages()

    m = unwrap(msg)
    assert m.id == 42
    assert m.sent == datetime.fromtimestamp(1_700_000_000, tz=UTC)
    assert m.subject == 'greetings'
    assert m.sender.full_name == 'Alice'
    assert m.server.string_id == 'example'
    assert m.content == 'hello world'
    assert m.permalink == 'https://example.zulipchat.com/#narrow/near/42'
