from datetime import datetime, timezone

import pytest

from app.models.ambience import Ambience, Filter, Range


@pytest.fixture
def sample_filter() -> Filter:
    return Filter(
        shuffle_rule=True,
        genres=["488"],
        moods=["Cool", "Lively"],
        energy=Range(min=40, max=80),
        tempo=Range(min=110, max=None),
        popularity=Range(min=35, max=None),
    )


@pytest.fixture
def sample_ambience(sample_filter: Filter) -> Ambience:
    return Ambience(
        uuid="test-uuid-1234",
        user_id="user-1",
        prompt="rainy afternoon jazz",
        fingerprint="abc123fingerprint",
        created_at=datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc),
        name="Rainy Afternoon Jazz",
        intension="A relaxed rainy-day atmosphere",
        publico="Remote workers and creatives",
        shuffle_rule=False,
        filters=[sample_filter],
    )
