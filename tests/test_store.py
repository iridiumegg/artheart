"""Tests for the flat-file store: dedup and name scrubbing."""
from artheart import store


def _report_dict():
    return {
        "title": "CBMAA Gallery 2",
        "location_path": "Crystal Bridges Museum / CBMAA Main",
        "generated_at": "2026-08-10T11:00:20",
        "generated_by": "ES2 - Nate Stewart (nstewart)",
        "parse_confidence": 1.0,
        "warnings": ["AHU 19: missing zone temp"],
        "readings": [{"zone": "AHU 2", "rh": 53.8, "rh_ts": None, "temp_f": 69.0}],
    }


def test_add_and_dedup():
    s = store.empty_store()
    assert store.add_report(s, _report_dict(), "msg-1") is True
    assert store.add_report(s, _report_dict(), "msg-1") is False  # duplicate
    assert len(s["reports"]) == 1


def test_scrubs_person_name_and_warnings():
    s = store.empty_store()
    store.add_report(s, _report_dict(), "msg-1")
    rec = s["reports"][0]
    assert "generated_by" not in rec
    assert "warnings" not in rec
    assert rec["gallery_title"] == "CBMAA Gallery 2"
    assert rec["gmail_msg_id"] == "msg-1"


def test_roundtrip(tmp_path):
    s = store.empty_store()
    store.add_report(s, _report_dict(), "msg-1")
    p = tmp_path / "readings.json"
    store.save_store(str(p), s)
    loaded = store.load_store(str(p))
    assert loaded == s
