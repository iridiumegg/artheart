"""Tests for the digest email builder (pure HTML/string, no network)."""
from artheart import email_digest


def _summary(excursions=None):
    return {
        "date": "2026-08-10",
        "snapshot_count": 1,
        "zone_count": 2,
        "excursion_count": len(excursions or []),
        "excursions": excursions or [],
        "zones": [
            {"zone": "AHU 2", "temp": {"latest": 69.0}, "rh": {"latest": 53.8},
             "temp_adherence": 100.0, "rh_adherence": 100.0, "in_band": True},
            {"zone": "AHU 13", "temp": {"latest": 72.2}, "rh": {"latest": 52.8},
             "temp_adherence": 0.0, "rh_adherence": 100.0, "in_band": False},
        ],
    }


def test_subject_clean_vs_excursions():
    assert email_digest.build_subject(_summary()) == \
        "CBMAA Gallery Conditions — 2026-08-10 — all zones in band"
    exc = [{"zone": "AHU 13", "metric": "temp", "value": 72.2,
            "band_lo": 68.0, "band_hi": 72.0, "at": "2026-08-10T11:00:20"}]
    assert "1 excursion" in email_digest.build_subject(_summary(exc))


def test_html_contains_zones_and_button():
    exc = [{"zone": "AHU 13", "metric": "temp", "value": 72.2,
            "band_lo": 68.0, "band_hi": 72.0, "at": "2026-08-10T11:00:20"}]
    html = email_digest.build_html(_summary(exc), "https://example.github.io/artheart/")
    assert "AHU 2" in html and "AHU 13" in html
    assert "72.2" in html                       # the excursion value
    assert "View full dashboard" in html        # CTA present with a URL
    assert "https://example.github.io/artheart/" in html


def test_html_omits_button_without_url():
    html = email_digest.build_html(_summary(), "")
    assert "View full dashboard" not in html
    assert "All zones within band" in html
