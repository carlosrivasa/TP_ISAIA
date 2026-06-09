from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.ambience import (
    Ambience,
    AmbienceContent,
    AmbienceRequest,
    Filter,
    Range,
)


def test_range_valid_min_max() -> None:
    r = Range(min=10.0, max=50.0)
    assert r.min == 10.0
    assert r.max == 50.0


def test_range_min_gt_max_raises() -> None:
    with pytest.raises(ValidationError):
        Range(min=80.0, max=20.0)


def test_range_defaults_to_none() -> None:
    r = Range()
    assert r.min is None
    assert r.max is None


def test_range_only_min() -> None:
    r = Range(min=40.0)
    assert r.min == 40.0
    assert r.max is None


def test_filter_defaults() -> None:
    f = Filter()
    assert f.genres == []
    assert f.moods == []
    assert f.explicit is False
    assert f.shuffle_rule is False
    assert f.tracks_exceptions == []
    assert f.popularity == Range()


def test_ambience_content_requires_name() -> None:
    with pytest.raises(ValidationError):
        AmbienceContent(
            name="",
            intension="x",
            publico="x",
            shuffle_rule=False,
            filters=[Filter()],
        )


def test_ambience_content_requires_at_least_one_filter() -> None:
    with pytest.raises(ValidationError):
        AmbienceContent(
            name="My Ambience",
            intension="x",
            publico="x",
            shuffle_rule=False,
            filters=[],
        )


def test_ambience_content_valid() -> None:
    content = AmbienceContent(
        name="Workout Mix",
        intension="High energy",
        publico="Gym-goers",
        shuffle_rule=True,
        filters=[Filter(genres=["488"], moods=["Lively"])],
    )
    assert content.name == "Workout Mix"
    assert len(content.filters) == 1


def test_ambience_request_too_short() -> None:
    with pytest.raises(ValidationError):
        AmbienceRequest(prompt="ab", user_id="u1")


def test_ambience_request_too_long() -> None:
    with pytest.raises(ValidationError):
        AmbienceRequest(prompt="x" * 2001, user_id="u1")


def test_ambience_request_valid() -> None:
    req = AmbienceRequest(prompt="rainy afternoon jazz", user_id="u1")
    assert req.user_id == "u1"


def test_ambience_round_trips_json() -> None:
    a = Ambience(
        uuid="test-uuid",
        user_id="u1",
        prompt="rainy afternoon jazz",
        fingerprint="abc123",
        created_at=datetime(2026, 6, 9, tzinfo=timezone.utc),
        name="Jazz",
        intension="Relaxed",
        publico="Everyone",
        shuffle_rule=False,
        filters=[Filter()],
    )
    data = a.model_dump_json()
    b = Ambience.model_validate_json(data)
    assert b.uuid == a.uuid
    assert b.fingerprint == a.fingerprint
