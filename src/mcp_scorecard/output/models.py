"""Pydantic models for scorecard output."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class Badge(BaseModel):
    key: str
    type: str  # "flag", "bool", "enum"
    label: str
    value: bool | str | None = None
    severity: str | None = None  # for flags: "critical", "warning", "info"
    level: str | None = None  # for enums: "good", "neutral", "warning", "critical", "new"


class PopularityMetrics(BaseModel):
    stars: int = 0
    forks: int = 0
    watchers: int = 0


class BadgeGroups(BaseModel):
    security: list[Badge] = Field(default_factory=list)
    provenance: list[Badge] = Field(default_factory=list)
    activity: list[Badge] = Field(default_factory=list)
    popularity: PopularityMetrics = Field(default_factory=PopularityMetrics)


class ServerScore(BaseModel):
    trust_score: int = Field(ge=0, le=100)
    trust_label: str
    scores: CategoryScores
    signals: dict[str, object]
    flags: list[str] = Field(default_factory=list)
    badges: BadgeGroups = Field(default_factory=BadgeGroups)
    verified_publisher: bool = False


class CategoryScores(BaseModel):
    provenance: int = Field(ge=0, le=100)
    maintenance: int = Field(ge=0, le=100)
    popularity: int = Field(ge=0, le=100)
    permissions: int = Field(ge=0, le=100)


class ScorecardIndex(BaseModel):
    version: str = "0.1.0"
    generated_at: datetime
    server_count: int
    servers: dict[str, ServerScore]


class FlagGroup(BaseModel):
    flag: str
    count: int
    servers: list[str]


class FlagsIndex(BaseModel):
    version: str = "0.1.0"
    generated_at: datetime
    flags: list[FlagGroup]


class ScoreBand(BaseModel):
    label: str
    min_score: int
    max_score: int
    count: int


class StatsIndex(BaseModel):
    version: str = "0.1.0"
    generated_at: datetime
    server_count: int
    servers_with_repo: int
    servers_with_packages: int
    score_distribution: list[ScoreBand]
    flag_summary: dict[str, int]
    top_servers: list[TopServer]
    average_trust_score: float
    median_trust_score: int


class TopServer(BaseModel):
    name: str
    trust_score: int
    trust_label: str
