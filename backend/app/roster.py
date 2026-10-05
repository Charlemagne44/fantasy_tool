from __future__ import annotations

from typing import Dict, List, Set

from .models import LineupPlayer, Player, Slot

DK_CLASSIC_SLOTS: List[Slot] = [
    "QB",
    "RB",
    "RB",
    "WR",
    "WR",
    "WR",
    "TE",
    "FLEX",
    "DST",
]

FLEX_ELIGIBLE = {"RB", "WR", "TE"}

DEFAULT_SALARY_CAP = 50_000


def aggression_score(player: Player, aggression: float) -> float:
    """Map aggression in [-1, 1] onto floor / median / ceiling."""
    a = max(-1.0, min(1.0, aggression))
    if a < 0:
        return player.projection + a * (player.projection - player.floor)
    if a > 0:
        return player.projection + a * (player.ceiling - player.projection)
    return player.projection


def assign_slots(players: List[Player], scores: Dict[str, float]) -> List[LineupPlayer]:
    """Assign DK Classic slots to a selected set of players."""
    by_pos: Dict[str, List[Player]] = {"QB": [], "RB": [], "WR": [], "TE": [], "DST": []}
    for player in players:
        by_pos[player.position].append(player)

    for pos_players in by_pos.values():
        pos_players.sort(key=lambda p: (-scores[p.id], -p.projection, p.salary, p.id))

    assigned: List[LineupPlayer] = []
    used_ids: Set[str] = set()

    def take(position: str, slot: Slot) -> None:
        pool = by_pos[position]
        while pool:
            player = pool.pop(0)
            if player.id in used_ids:
                continue
            used_ids.add(player.id)
            assigned.append(
                LineupPlayer(
                    id=player.id,
                    name=player.name,
                    position=player.position,
                    slot=slot,
                    team=player.team,
                    opp=player.opp,
                    salary=player.salary,
                    projection=player.projection,
                    floor=player.floor,
                    ceiling=player.ceiling,
                    score=scores[player.id],
                )
            )
            return
        raise ValueError(f"Unable to fill slot {slot}")

    take("QB", "QB")
    take("RB", "RB")
    take("RB", "RB")
    take("WR", "WR")
    take("WR", "WR")
    take("WR", "WR")
    take("TE", "TE")
    take("DST", "DST")

    # Remaining FLEX-eligible player
    flex_candidates = [
        p for p in players if p.id not in used_ids and p.position in FLEX_ELIGIBLE
    ]
    if len(flex_candidates) != 1:
        raise ValueError("Expected exactly one FLEX player remaining")
    flex = flex_candidates[0]
    assigned.append(
        LineupPlayer(
            id=flex.id,
            name=flex.name,
            position=flex.position,
            slot="FLEX",
            team=flex.team,
            opp=flex.opp,
            salary=flex.salary,
            projection=flex.projection,
            floor=flex.floor,
            ceiling=flex.ceiling,
            score=scores[flex.id],
        )
    )

    # Preserve DK Classic slot order (including duplicate RB/WR labels).
    ordered: List[LineupPlayer] = []
    remaining = assigned[:]
    for slot in DK_CLASSIC_SLOTS:
        for i, player in enumerate(remaining):
            if player.slot == slot:
                ordered.append(player)
                remaining.pop(i)
                break

    return ordered
