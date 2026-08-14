"""Parser for CBMAA WebCTRL gallery-condition snapshot PDFs.

A report is a single-page WebCTRL point snapshot: a title, a location path,
one table (Location / Humidity / Zone Temp), and a footer with the
generated-by user and generation timestamp.

Validated against tests/samples/CBMAA_Gallery_2_sample.pdf.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import pdfplumber

# "53.8 @ 08/10/2026 09:14:55 AM"
_HUMIDITY_RE = re.compile(r"^\s*([\d.]+)\s*@\s*(.+?)\s*$")
# footer: "ES2 - Nate Stewart (nstewart) 08/10/2026 11:00:20 AM Page 1 of 1"
_FOOTER_RE = re.compile(r"^(.*?\))\s+(\d{2}/\d{2}/\d{4}\s+[\d:]+\s+[AP]M)")
_FLOAT_RE = re.compile(r"^[\d.]+$")
_TS_FMT = "%m/%d/%Y %I:%M:%S %p"


@dataclass
class Reading:
    zone: str
    rh: Optional[float] = None
    rh_ts: Optional[datetime] = None
    temp_f: Optional[float] = None


@dataclass
class Report:
    title: Optional[str] = None
    location_path: Optional[str] = None
    generated_at: Optional[datetime] = None
    generated_by: Optional[str] = None
    readings: list[Reading] = field(default_factory=list)
    parse_confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["generated_at"] = self.generated_at.isoformat() if self.generated_at else None
        for r in d["readings"]:
            r["rh_ts"] = r["rh_ts"].isoformat() if r["rh_ts"] else None
        return d


def _parse_ts(raw: str) -> Optional[datetime]:
    try:
        return datetime.strptime(raw.strip(), _TS_FMT)
    except (ValueError, AttributeError):
        return None


def _parse_float(raw: Optional[str]) -> Optional[float]:
    raw = (raw or "").strip()
    return float(raw) if _FLOAT_RE.match(raw) else None


def normalize_zone(name: Optional[str]) -> str:
    """Canonical AHU label: strip any '(descriptor)' and unify the separator.

    'AHU 13 (Gallery 3/4)' -> 'AHU 13',  'AHU-18 (Gallery 6 N)' -> 'AHU 18'.
    """
    name = (name or "").split("(", 1)[0].strip()
    name = re.sub(r"^AHU\s*-\s*", "AHU ", name)
    return re.sub(r"\s+", " ", name).strip()


def parse_report(path: str) -> Report:
    """Parse a WebCTRL gallery-condition PDF into a structured Report."""
    report = Report()
    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            report.warnings.append("empty PDF: no pages")
            return report
        page = pdf.pages[0]
        text = page.extract_text() or ""
        tables = page.extract_tables()

    lines = [ln for ln in text.splitlines() if ln.strip()]

    # Title = first non-empty line.
    if lines:
        report.title = lines[0].strip()

    # Location path.
    for ln in lines:
        if ln.lower().startswith("location:"):
            report.location_path = ln.split(":", 1)[1].strip()
            break

    # Footer (last line): generated_by + generated_at.
    if lines:
        m = _FOOTER_RE.match(lines[-1])
        if m:
            report.generated_by = m.group(1).strip()
            report.generated_at = _parse_ts(m.group(2))

    # Readings table.
    if not tables:
        report.warnings.append("no table found")
    else:
        for row in tables[0][1:]:  # skip header
            if not row or not (row[0] or "").strip():
                continue
            zone = normalize_zone(row[0])
            rh, rh_ts = None, None
            hm = _HUMIDITY_RE.match((row[1] or "").strip()) if len(row) > 1 else None
            if hm:
                rh = float(hm.group(1))
                rh_ts = _parse_ts(hm.group(2))
            temp_f = _parse_float(row[2] if len(row) > 2 else None)
            if temp_f is None and (len(row) < 3 or not (row[2] or "").strip()):
                report.warnings.append(f"{zone}: missing zone temp")
            report.readings.append(Reading(zone=zone, rh=rh, rh_ts=rh_ts, temp_f=temp_f))

    report.parse_confidence = _confidence(report)
    return report


def _confidence(report: Report) -> float:
    """Cheap heuristic so bad parses surface instead of corrupting charts."""
    score = 0.0
    if report.title:
        score += 0.2
    if report.location_path:
        score += 0.2
    if report.generated_at:
        score += 0.2
    if report.readings:
        score += 0.2
        complete = sum(1 for r in report.readings if r.rh is not None)
        score += 0.2 * (complete / len(report.readings))
    return round(score, 2)


def find_excursions(report: Report, temp_band=(68.0, 72.0), rh_band=(45.0, 55.0)):
    """Derive out-of-band events (no alarm data exists in the report itself).

    Bands are placeholders; real per-zone bands live in the `zones` table.
    """
    out = []
    tlo, thi = temp_band
    rlo, rhi = rh_band
    for r in report.readings:
        if r.temp_f is not None and not (tlo <= r.temp_f <= thi):
            out.append({"zone": r.zone, "metric": "temp", "value": r.temp_f,
                        "band_lo": tlo, "band_hi": thi})
        if r.rh is not None and not (rlo <= r.rh <= rhi):
            out.append({"zone": r.zone, "metric": "rh", "value": r.rh,
                        "band_lo": rlo, "band_hi": rhi})
    return out


if __name__ == "__main__":
    import json
    import sys

    rep = parse_report(sys.argv[1])
    print(json.dumps(rep.as_dict(), indent=2))
    print("excursions:", json.dumps(find_excursions(rep), indent=2))
