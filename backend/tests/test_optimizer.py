from typing import List, Optional

import pytest

from backend.app.models import OptimizeRequest, Player
from backend.app.optimizer import OptimizeError, optimize_lineups
from backend.app.roster import aggression_score


def P(
    pid: str,
    name: str,
    pos: str,
    salary: int,
    proj: float,
    floor: Optional[float] = None,
    ceiling: Optional[float] = None,
) -> Player:
    return Player(
        id=pid,
        name=name,
        position=pos,  # type: ignore[arg-type]
        team="TM",
        opp="OPP",
        salary=salary,
        projection=proj,
        floor=floor if floor is not None else proj - 5,
        ceiling=ceiling if ceiling is not None else proj + 10,
    )


def mini_pool() -> List[Player]:
    # Constructed so the median-optimal lineup is deterministic.
    return [
        P("qb1", "QB High", "QB", 7000, 20),
        P("qb2", "QB Low", "QB", 5000, 10),
        P("rb1", "RB1", "RB", 7000, 18),
        P("rb2", "RB2", "RB", 6000, 16),
        P("rb3", "RB3", "RB", 4000, 10),
        P("wr1", "WR1", "WR", 7000, 17),
        P("wr2", "WR2", "WR", 6000, 15),
        P("wr3", "WR3", "WR", 5000, 13),
        P("wr4", "WR4", "WR", 3000, 8),
        P("te1", "TE1", "TE", 5000, 12),
        P("te2", "TE2", "TE", 3000, 7),
        P("dst1", "DST1", "DST", 3000, 8),
        P("dst2", "DST2", "DST", 2000, 5),
        # High ceiling / low median WR to test aggression
        P("wr_ceil", "WR Ceiling", "WR", 5500, 11, floor=4, ceiling=30),
        # High floor / lower ceiling
        P("wr_floor", "WR Floor", "WR", 5500, 12, floor=11, ceiling=14),
    ]


def test_aggression_score_endpoints():
    p = P("1", "X", "WR", 5000, 10, floor=4, ceiling=20)
    assert aggression_score(p, -1) == 4
    assert aggression_score(p, 0) == 10
    assert aggression_score(p, 1) == 20
    assert aggression_score(p, 0.5) == 15


def test_optimal_median_lineup():
    # Cap 50000; median-optimal should take top skill + cheapest viable pieces.
    req = OptimizeRequest(players=mini_pool(), salary_cap=50000, aggression=0.0)
    lineups = optimize_lineups(req)
    assert len(lineups) == 1
    lineup = lineups[0]
    ids = {p.id for p in lineup.players}
    assert "qb1" in ids
    assert "dst1" in ids or "dst2" in ids
    assert len(lineup.players) == 9
    assert sum(1 for p in lineup.players if p.slot == "FLEX") == 1
    assert lineup.total_salary <= 50000
    slots = [p.slot for p in lineup.players]
    assert slots == ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"]


def test_lock_and_exclude():
    req = OptimizeRequest(
        players=mini_pool(),
        salary_cap=50000,
        locked_ids=["qb2"],
        excluded_ids=["qb1"],
    )
    lineup = optimize_lineups(req)[0]
    ids = {p.id for p in lineup.players}
    assert "qb2" in ids
    assert "qb1" not in ids


def test_top_n_diversity():
    req = OptimizeRequest(
        players=mini_pool(),
        salary_cap=50000,
        num_lineups=3,
        min_unique=1,
    )
    lineups = optimize_lineups(req)
    assert len(lineups) >= 2
    sets = [frozenset(p.id for p in lu.players) for lu in lineups]
    assert len(sets[0] ^ sets[1]) >= 2  # at least one player different each way


def test_aggression_prefers_ceiling():
    # Tight cap forces a choice between wr_ceil and wr_floor-like options.
    pool = [
        P("qb1", "QB", "QB", 6000, 18),
        P("rb1", "RB1", "RB", 5000, 14),
        P("rb2", "RB2", "RB", 5000, 13),
        P("wr1", "WR1", "WR", 5000, 12),
        P("wr2", "WR2", "WR", 5000, 11),
        P("wr_ceil", "WR Ceiling", "WR", 5000, 10, floor=3, ceiling=28),
        P("wr_floor", "WR Floor", "WR", 5000, 10.5, floor=9, ceiling=12),
        P("te1", "TE", "TE", 4000, 9),
        P("dst1", "DST", "DST", 3000, 7),
        P("rb3", "RB3", "RB", 3000, 6),
    ]
    # With 9 slots this pool is exactly fillable with leftover rb3 as flex path.
    gpp = optimize_lineups(
        OptimizeRequest(players=pool, salary_cap=43000, aggression=1.0)
    )[0]
    cash = optimize_lineups(
        OptimizeRequest(players=pool, salary_cap=43000, aggression=-1.0)
    )[0]
    gpp_ids = {p.id for p in gpp.players}
    cash_ids = {p.id for p in cash.players}
    assert "wr_ceil" in gpp_ids
    assert "wr_floor" in cash_ids


def test_infeasible_raises():
    with pytest.raises(OptimizeError):
        optimize_lineups(
            OptimizeRequest(
                players=mini_pool(),
                salary_cap=1000,
            )
        )
