import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.ambience import Ambience, Filter
from app.models.errors import AmbienceStorageError
from app.persistence.local_store import LocalStore


def _make_ambience(uuid: str = "test-uuid") -> Ambience:
    return Ambience(
        uuid=uuid,
        user_id="u1",
        prompt="rainy afternoon jazz",
        fingerprint="fp1",
        created_at=datetime(2026, 6, 9, tzinfo=timezone.utc),
        name="Jazz",
        intension="Relaxed",
        publico="Everyone",
        shuffle_rule=False,
        filters=[Filter(genres=["488"], moods=["Cool"])],
    )


def test_save_writes_json_file(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    a = _make_ambience()
    store.save(a)
    expected_path = tmp_path / f"{a.uuid}.json"
    assert expected_path.exists()


def test_save_content_round_trips(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    a = _make_ambience()
    store.save(a)
    raw = (tmp_path / f"{a.uuid}.json").read_text()
    data = json.loads(raw)
    assert data["uuid"] == a.uuid
    assert data["fingerprint"] == a.fingerprint
    assert data["filters"][0]["genres"] == ["488"]


def test_save_creates_data_dir_if_missing(tmp_path: Path) -> None:
    new_dir = tmp_path / "subdir" / "data"
    store = LocalStore(data_dir=new_dir)
    store.save(_make_ambience())
    assert new_dir.exists()


def test_save_uses_uuid_as_filename(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    store.save(_make_ambience("my-unique-id"))
    assert (tmp_path / "my-unique-id.json").exists()


def test_save_raises_storage_error_on_write_failure(tmp_path: Path) -> None:
    store = LocalStore(data_dir=tmp_path)
    a = _make_ambience()
    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        with pytest.raises(AmbienceStorageError) as exc_info:
            store.save(a)
    assert isinstance(exc_info.value.__cause__, OSError)
