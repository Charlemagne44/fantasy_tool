from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


Position = Literal["QB", "RB", "WR", "TE", "DST"]
Slot = Literal["QB", "RB", "WR", "TE", "FLEX", "DST"]


class Player(BaseModel):
    id: str
    name: str
    position: Position
    team: str
    opp: str
    salary: int = Field(gt=0)
    projection: float  # DK Proj / median
    floor: float
    ceiling: float
    value: float = 0.0
    small_field_own: float = 0.0
    large_field_own: float = 0.0


class PlayersResponse(BaseModel):
    players: List[Player]


class OptimizeRequest(BaseModel):
    players: List[Player]
    salary_cap: int = Field(default=50_000, gt=0)
    aggression: float = Field(default=0.0, ge=-1.0, le=1.0)
    locked_ids: List[str] = Field(default_factory=list)
    excluded_ids: List[str] = Field(default_factory=list)
    num_lineups: int = Field(default=1, ge=1, le=20)
    min_unique: int = Field(default=1, ge=1, le=3)
    min_floor: Optional[float] = Field(default=None, ge=0.0)


class LineupPlayer(BaseModel):
    id: str
    name: str
    position: Position
    slot: Slot
    team: str
    opp: str
    salary: int
    projection: float
    floor: float
    ceiling: float
    score: float


class Lineup(BaseModel):
    rank: int
    players: List[LineupPlayer]
    total_salary: int
    leftover_salary: int
    total_projection: float
    total_floor: float
    total_ceiling: float
    total_score: float


class OptimizeResponse(BaseModel):
    lineups: List[Lineup]
    salary_cap: int
    aggression: float
