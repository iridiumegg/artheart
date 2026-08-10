"""Smoke tests for the WebCTRL report parser, against the real sample PDF."""
import os
from datetime import datetime

from artheart.parser import parse_report, find_excursions

SAMPLE = os.path.join(os.path.dirname(__file__), "samples", "CBMAA_Gallery_2_sample.pdf")


def test_header_fields():
    r = parse_report(SAMPLE)
    assert r.title == "CBMAA Gallery 2"
    assert r.location_path == "Crystal Bridges Museum / CBMAA Main / 2nd Floor / AHU 1"
    assert r.generated_at == datetime(2026, 8, 10, 11, 0, 20)
    assert "nstewart" in r.generated_by
    assert r.parse_confidence >= 0.9


def test_readings():
    r = parse_report(SAMPLE)
    assert len(r.readings) == 7
    ahu2 = r.readings[0]
    assert ahu2.zone == "AHU 2"
    assert ahu2.rh == 53.8
    assert ahu2.temp_f == 69.0
    assert ahu2.rh_ts == datetime(2026, 8, 10, 9, 14, 55)
    # AHU 19 has no zone temp in the source report.
    ahu19 = r.readings[-1]
    assert ahu19.zone == "AHU 19"
    assert ahu19.temp_f is None
    assert ahu19.rh == 48.9


def test_excursions_against_real_bands():
    # Temp band 68-72F, RH 45-55%. AHU 13 reads 72.2F -> one temp excursion.
    r = parse_report(SAMPLE)
    exc = find_excursions(r)
    assert exc == [
        {"zone": "AHU 13", "metric": "temp", "value": 72.2,
         "band_lo": 68.0, "band_hi": 72.0}
    ]
