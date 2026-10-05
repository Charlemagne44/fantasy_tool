from pathlib import Path

import pytest

from backend.app.csv_parser import CsvParseError, parse_etr_csv, position_counts

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "etr_dk_main_slate.csv"

MINI_CSV = """Player,DK Pos,Team,Opp,DK Salary,DK Proj,DK Value,Small Field,Large Field,DK Floor,DK Ceiling,id
Alpha QB,QB,AAA,BBB,"$7,000",18.0,1.0,10.0%,12.0%,10.0,28.0,1
Beta RB,RB,AAA,BBB,"$6,000",15.0,1.0,8.0%,9.0%,7.0,25.0,2
Vikings ,DST,MIN,@CHI,"$3,000",8.0,0.5,5.0%,6.0%,2.0,14.0,3
"""


def test_parse_sample_csv():
    players = parse_etr_csv(SAMPLE.open("rb"))
    assert len(players) == 330
    counts = position_counts(players)
    assert counts["QB"] == 24
    assert counts["RB"] == 83
    assert counts["WR"] == 120
    assert counts["TE"] == 79
    assert counts["DST"] == 24

    first = next(p for p in players if p.name == "Jaxon Smith-Njigba")
    assert first.salary == 9100
    assert first.projection == 21.9
    assert first.floor == 8.9
    assert first.ceiling == 36.8
    assert first.small_field_own == 9.5
    assert first.large_field_own == 10.4
    assert first.id == "44312562"


def test_salary_and_percent_and_trim():
    players = parse_etr_csv(MINI_CSV.encode("utf-8"))
    assert players[0].salary == 7000
    assert players[0].small_field_own == 10.0
    dst = next(p for p in players if p.position == "DST")
    assert dst.name == "Vikings"
    assert dst.salary == 3000


def test_missing_column_error():
    bad = MINI_CSV.replace("DK Floor,", "Floor,")
    with pytest.raises(CsvParseError, match="Missing required columns"):
        parse_etr_csv(bad.encode("utf-8"))
