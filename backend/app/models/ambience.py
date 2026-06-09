from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class Range(BaseModel):
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def _validate_order(self) -> Range:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must be <= max")
        return self


class Filter(BaseModel):
    shuffle_rule: bool = False
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    album_release_dates: list[str] = Field(default_factory=list)
    artist_origin_regions: list[str] = Field(default_factory=list)
    artist_origin_countries: list[str] = Field(default_factory=list)
    explicit: bool = False
    tracks_exceptions: list[str] = Field(default_factory=list)
    popularity: Range = Field(default_factory=Range)
    acousticness: Range = Field(default_factory=Range)
    danceability: Range = Field(default_factory=Range)
    energy: Range = Field(default_factory=Range)
    instrumentalness: Range = Field(default_factory=Range)
    liveness: Range = Field(default_factory=Range)
    loudness: Range = Field(default_factory=Range)
    speechiness: Range = Field(default_factory=Range)
    tempo: Range = Field(default_factory=Range)
    valence: Range = Field(default_factory=Range)


class AmbienceContent(BaseModel):
    name: str = Field(min_length=1)
    intension: str
    publico: str
    shuffle_rule: bool = False
    filters: list[Filter] = Field(min_length=1)


class AmbienceRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    user_id: str = Field(min_length=1)


class Ambience(BaseModel):
    uuid: str
    user_id: str
    prompt: str
    fingerprint: str
    created_at: datetime
    name: str
    intension: str
    publico: str
    shuffle_rule: bool
    filters: list[Filter]
