from __future__ import annotations

from typing import Dict, List, Optional, Set

from pulp import LpBinary, LpMaximize, LpProblem, LpStatus, LpVariable, lpSum, value

from .models import Lineup, OptimizeRequest, Player
from .roster import aggression_score, assign_slots


class OptimizeError(ValueError):
    """Raised when lineup optimization fails."""


def _validate_request(req: OptimizeRequest) -> Dict[str, Player]:
    if not req.players:
        raise OptimizeError("Player pool is empty")

    by_id: Dict[str, Player] = {}
    for player in req.players:
        if player.id in by_id:
            raise OptimizeError(f"Duplicate player id in pool: {player.id}")
        by_id[player.id] = player

    locked = set(req.locked_ids)
    excluded = set(req.excluded_ids)
    overlap = locked & excluded
    if overlap:
        raise OptimizeError(
            "Players cannot be both locked and excluded: " + ", ".join(sorted(overlap))
        )

    unknown = (locked | excluded) - set(by_id)
    if unknown:
        raise OptimizeError(
            "Unknown player ids in locks/excludes: " + ", ".join(sorted(unknown))
        )

    for player_id in excluded:
        by_id.pop(player_id, None)

    # Ensure locked players remain
    for player_id in locked:
        if player_id not in by_id:
            raise OptimizeError(f"Locked player missing from pool: {player_id}")

    return by_id


def _solve_once(
    players: List[Player],
    scores: Dict[str, float],
    salary_cap: int,
    locked_ids: Set[str],
    min_floor: Optional[float],
    banned_lineups: List[Set[str]],
    min_unique: int,
) -> Optional[List[Player]]:
    prob = LpProblem("dk_classic_lineup", LpMaximize)
    x = {p.id: LpVariable(f"x_{p.id}", cat=LpBinary) for p in players}

    prob += lpSum(scores[p.id] * x[p.id] for p in players)

    prob += lpSum(p.salary * x[p.id] for p in players) <= salary_cap, "salary_cap"
    prob += lpSum(x[p.id] for p in players) == 9, "roster_size"

    qb = [p for p in players if p.position == "QB"]
    rb = [p for p in players if p.position == "RB"]
    wr = [p for p in players if p.position == "WR"]
    te = [p for p in players if p.position == "TE"]
    dst = [p for p in players if p.position == "DST"]
    flex_pool = rb + wr + te

    prob += lpSum(x[p.id] for p in qb) == 1, "qb"
    prob += lpSum(x[p.id] for p in dst) == 1, "dst"
    prob += lpSum(x[p.id] for p in rb) >= 2, "rb_min"
    prob += lpSum(x[p.id] for p in wr) >= 3, "wr_min"
    prob += lpSum(x[p.id] for p in te) >= 1, "te_min"
    prob += lpSum(x[p.id] for p in flex_pool) == 7, "skill_with_flex"

    if min_floor is not None:
        prob += lpSum(p.floor * x[p.id] for p in players) >= min_floor, "min_floor"

    for player_id in locked_ids:
        if player_id in x:
            prob += x[player_id] == 1, f"lock_{player_id}"

    for i, prior in enumerate(banned_lineups):
        # Require at least min_unique players different from a prior lineup:
        # overlap <= 9 - min_unique
        max_overlap = 9 - min_unique
        present = [pid for pid in prior if pid in x]
        if present:
            prob += lpSum(x[pid] for pid in present) <= max_overlap, f"diversity_{i}"

    status = prob.solve(pulp_solver())
    if LpStatus[status] != "Optimal":
        return None

    selected = [p for p in players if value(x[p.id]) is not None and value(x[p.id]) > 0.5]
    if len(selected) != 9:
        return None
    return selected


def pulp_solver():
    """Return HiGHS (ARM-friendly); fall back to CBC if needed."""
    from pulp import HiGHS, PULP_CBC_CMD

    try:
        return HiGHS(msg=False)
    except Exception:  # noqa: BLE001
        return PULP_CBC_CMD(msg=False)


def optimize_lineups(req: OptimizeRequest) -> List[Lineup]:
    by_id = _validate_request(req)
    locked_ids = set(req.locked_ids)
    excluded_ids = set(req.excluded_ids)

    # Locked players that were not excluded (excluded already removed)
    pool = [p for p in by_id.values() if p.id not in excluded_ids]
    scores = {p.id: aggression_score(p, req.aggression) for p in pool}

    # Quick feasibility checks
    locked_players = [by_id[i] for i in locked_ids]
    if sum(p.salary for p in locked_players) > req.salary_cap:
        raise OptimizeError("Locked players exceed the salary cap")

    lineups: List[Lineup] = []
    banned: List[Set[str]] = []

    for rank in range(1, req.num_lineups + 1):
        selected = _solve_once(
            players=pool,
            scores=scores,
            salary_cap=req.salary_cap,
            locked_ids=locked_ids,
            min_floor=req.min_floor,
            banned_lineups=banned,
            min_unique=req.min_unique,
        )
        if selected is None:
            if rank == 1:
                raise OptimizeError(
                    "No valid lineup found for the given constraints"
                )
            break

        slotted = assign_slots(selected, scores)
        total_salary = sum(p.salary for p in slotted)
        total_projection = sum(p.projection for p in slotted)
        total_floor = sum(p.floor for p in slotted)
        total_ceiling = sum(p.ceiling for p in slotted)
        total_score = sum(p.score for p in slotted)

        lineups.append(
            Lineup(
                rank=rank,
                players=slotted,
                total_salary=total_salary,
                leftover_salary=req.salary_cap - total_salary,
                total_projection=round(total_projection, 2),
                total_floor=round(total_floor, 2),
                total_ceiling=round(total_ceiling, 2),
                total_score=round(total_score, 2),
            )
        )
        banned.append({p.id for p in selected})

    return lineups
