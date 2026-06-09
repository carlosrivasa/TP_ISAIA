from typing import Protocol

from app.models.ambience import Ambience


class AmbienceStore(Protocol):
    def save(self, ambience: Ambience) -> None: ...
