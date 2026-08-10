"""Tests for the daily rollup / excursion derivation."""
from artheart import aggregate, store


def _store_two_snapshots():
    s = store.empty_store()
    # 09:00 snapshot: AHU 2 fine, AHU 13 hot (72.2 > 72)
    store.add_report(s, {
        "title": "CBMAA", "location_path": "x", "generated_at": "2026-08-10T09:00:00",
        "parse_confidence": 1.0,
        "readings": [
            {"zone": "AHU 2", "rh": 50.0, "rh_ts": None, "temp_f": 70.0},
            {"zone": "AHU 13", "rh": 52.0, "rh_ts": None, "temp_f": 72.2},
        ],
    }, "m1")
    # 11:00 snapshot: AHU 13 recovered, AHU 2 RH low (44 < 45)
    store.add_report(s, {
        "title": "CBMAA", "location_path": "x", "generated_at": "2026-08-10T11:00:00",
        "parse_confidence": 1.0,
        "readings": [
            {"zone": "AHU 2", "rh": 44.0, "rh_ts": None, "temp_f": 70.5},
            {"zone": "AHU 13", "rh": 51.0, "rh_ts": None, "temp_f": 71.0},
        ],
    }, "m2")
    return s


def test_summary_shape_and_counts():
    summ = aggregate.daily_summary(_store_two_snapshots(), "2026-08-10")
    assert summ["snapshot_count"] == 2
    assert summ["zone_count"] == 2
    # AHU 13 temp excursion + AHU 2 rh excursion = 2
    assert summ["excursion_count"] == 2
    metrics = {(e["zone"], e["metric"]) for e in summ["excursions"]}
    assert metrics == {("AHU 13", "temp"), ("AHU 2", "rh")}


def test_zone_stats_and_numeric_sort():
    summ = aggregate.daily_summary(_store_two_snapshots(), "2026-08-10")
    zones = [z["zone"] for z in summ["zones"]]
    assert zones == ["AHU 2", "AHU 13"]  # numeric, not lexical ("13" < "2" lexically)
    ahu2 = summ["zones"][0]
    assert ahu2["temp"]["latest"] == 70.5
    assert ahu2["temp"]["max"] == 70.5
    assert ahu2["rh"]["min"] == 44.0
    # AHU 2: 1 of 2 RH samples in band -> 50% adherence
    assert ahu2["rh_adherence"] == 50.0
    assert ahu2["temp_adherence"] == 100.0


def test_other_days_excluded():
    s = _store_two_snapshots()
    summ = aggregate.daily_summary(s, "2026-08-11")
    assert summ["snapshot_count"] == 0
    assert summ["zones"] == []


def test_intraday_series_present():
    summ = aggregate.daily_summary(_store_two_snapshots(), "2026-08-10")
    ahu2 = summ["zones"][0]
    assert [p["value"] for p in ahu2["temp_series"]] == [70.0, 70.5]
    assert [p["value"] for p in ahu2["rh_series"]] == [50.0, 44.0]


def test_build_dashboard():
    s = _store_two_snapshots()
    dash = aggregate.build_dashboard(s)
    assert dash["dates"] == ["2026-08-10"]
    assert dash["latest"] == "2026-08-10"
    assert dash["temp_band"] == [68.0, 72.0]
    assert "2026-08-10" in dash["days"]
    assert dash["days"]["2026-08-10"]["zone_count"] == 2
