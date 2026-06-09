from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.models.ambience import Ambience, AmbienceRequest
from app.persistence.interfaces import AmbienceStore
from app.rag.interfaces import Pipeline


class AmbienceService:
    def __init__(self, pipeline: Pipeline, store: AmbienceStore) -> None:
        self._pipeline = pipeline
        self._store = store

    def create(self, request: AmbienceRequest) -> Ambience:
        content = self._pipeline.run(request.prompt)
        ambience = Ambience(
            uuid=str(uuid.uuid4()),
            user_id=request.user_id,
            prompt=request.prompt,
            fingerprint=self._fingerprint(request.user_id, request.prompt),
            created_at=datetime.now(timezone.utc),
            name=content.name,
            intension=content.intension,
            publico=content.publico,
            shuffle_rule=content.shuffle_rule,
            filters=content.filters,
        )
        self._store.save(ambience)
        return ambience

    @staticmethod
    def _fingerprint(user_id: str, prompt: str) -> str:
        normalized = " ".join(prompt.strip().lower().split())
        payload = f"{user_id}:{normalized}".encode()
        return hashlib.sha256(payload).hexdigest()
