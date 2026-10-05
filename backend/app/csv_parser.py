from __future__ import annotations

import io
from typing import BinaryIO, Dict, List, TextIO, Union

import pandas as pd

from .models import Player, Position

REQUIRED_COLUMNS = [
    "Player",
    "DK Pos",
    "Team",
    "Opp",
    "DK Salary",
    "DK Proj",
    "DK Value",
    "Small Field",
    "Large Field",
    "DK Floor",
    "DK Ceiling",
    "id",
]

VALID_POSITIONS: set[str] = {"QB", "RB", "WR", "TE", "DST"}


class CsvParseError(ValueError):
    """Raised when an ETR CSV cannot be parsed."""


def _parse_salary(value: object) -> int:
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        raise CsvParseError("Empty salary value")
    return int(float(text))


def _parse_percent(value: object) -> float:
    text = str(value).strip().replace("%", "")
    if not text:
        return 0.0
    return float(text)


def _parse_float(value: object, field: str) -> float:
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        raise CsvParseError(f"Missing {field}")
    return float(text)


def parse_etr_csv(source: Union[str, BinaryIO, TextIO, bytes]) -> List[Player]:
    """Parse an Establish The Run DraftKings Main Slate CSV."""
    if isinstance(source, bytes):
        buffer: Union[str, BinaryIO, TextIO] = io.BytesIO(source)
    else:
        buffer = source

    try:
        df = pd.read_csv(buffer, dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001 - surface as parse error
        raise CsvParseError(f"Unable to read CSV: {exc}") from exc

    df.columns = [str(c).strip() for c in df.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise CsvParseError(
            "Missing required columns: " + ", ".join(missing)
        )

    players: List[Player] = []
    seen_ids = set()

    for idx, row in df.iterrows():
        player_id = str(row["id"]).strip()
        if not player_id:
            raise CsvParseError(f"Row {idx}: missing id")
        if player_id in seen_ids:
            raise CsvParseError(f"Duplicate player id: {player_id}")
        seen_ids.add(player_id)

        position = str(row["DK Pos"]).strip().upper()
        if position not in VALID_POSITIONS:
            raise CsvParseError(
                f"Row {idx}: invalid DK Pos '{row['DK Pos']}'"
            )

        try:
            salary = _parse_salary(row["DK Salary"])
            projection = _parse_float(row["DK Proj"], "DK Proj")
            floor = _parse_float(row["DK Floor"], "DK Floor")
            ceiling = _parse_float(row["DK Ceiling"], "DK Ceiling")
            value = _parse_float(row["DK Value"], "DK Value") if str(row["DK Value"]).strip() else 0.0
            small_own = _parse_percent(row["Small Field"])
            large_own = _parse_percent(row["Large Field"])
        except (ValueError, CsvParseError) as exc:
            raise CsvParseError(f"Row {idx} ({player_id}): {exc}") from exc

        if salary <= 0:
            raise CsvParseError(f"Row {idx}: non-positive salary")

        players.append(
            Player(
                id=player_id,
                name=str(row["Player"]).strip(),
                position=position,  # type: ignore[arg-type]
                team=str(row["Team"]).strip(),
                opp=str(row["Opp"]).strip(),
                salary=salary,
                projection=projection,
                floor=floor,
                ceiling=ceiling,
                value=value,
                small_field_own=small_own,
                large_field_own=large_own,
            )
        )

    if not players:
        raise CsvParseError("CSV contained no players")

    return players


def position_counts(players: List[Player]) -> Dict[Position, int]:
    counts: Dict[Position, int] = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DST": 0}
    for player in players:
        counts[player.position] += 1
    return counts
