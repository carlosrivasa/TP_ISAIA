from __future__ import annotations

import json

from app.rag.interfaces import Doc, LLMRequest


class NoOpRetriever:
    def retrieve(self, prompt: str) -> list[Doc]:
        return []


class MockPromptBuilder:
    def build(self, prompt: str, context: list[Doc]) -> LLMRequest:
        return LLMRequest(system="You are a music ambience generator.", user=prompt)


_MOCK_RESPONSE: dict[str, object] = {
    "name": "Canned Mock Ambience",
    "intension": "A deterministic mock ambience for skeleton testing.",
    "publico": "Developers verifying the end-to-end skeleton.",
    "shuffle_rule": False,
    "filters": [
        {
            "shuffle_rule": True,
            "genres": ["488"],
            "moods": ["Cool", "Lively"],
            "album_release_dates": ["2010s"],
            "artist_origin_regions": [],
            "artist_origin_countries": [],
            "explicit": False,
            "tracks_exceptions": [],
            "popularity": {"min": 35, "max": None},
            "acousticness": {"min": None, "max": None},
            "danceability": {"min": None, "max": None},
            "energy": {"min": 40, "max": 80},
            "instrumentalness": {"min": None, "max": None},
            "liveness": {"min": None, "max": None},
            "loudness": {"min": None, "max": None},
            "speechiness": {"min": None, "max": None},
            "tempo": {"min": 110, "max": None},
            "valence": {"min": None, "max": None},
        }
    ],
}


class MockProvider:
    def generate(self, req: LLMRequest) -> str:
        return json.dumps(_MOCK_RESPONSE)
