"""Roll the stored readings up into a per-day dashboard summary.

Dependency-free so it tests without pdfplumber.
"""
from __future__ import annotations

from typing import Any, Optional

from . import config


def _in_band(value: Optional[float], band: tuple[float, float]) -> Optional[bool]:
    if value is None:
        return None
    return band[0] <= value <= band[1]


def _stats(values: list[float]) -> dict[str, Optional[float]]:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"min": None, "max": None, "avg": None, "latest": None}
    return {
        "min": round(min(vals), 1),
        "max": round(max(vals), 1),
        "avg": round(sum(vals) / len(vals), 1),
        "latest": round(vals[-1], 1),
    }


def daily_summary(store: dict[str, Any], date_str: str) -> dict[str, Any]:
    """Summarize all snapshots whose generated_at falls on `date_str` (YYYY-MM-DD).

    Returns a JSON-ready dict the dashboard/email consume directly.
    """
    reports = [
        r for r in store.get("reports", [])
        if (r.get("generated_at") or "").startswith(date_str)
    ]
    reports.sort(key=lambda r: r.get("generated_at") or "")

    # zone -> ordered lists of readings across the day's snapshots
    by_zone: dict[str, dict[str, list]] = {}
    for rep in reports:
        for rd in rep.get("readings", []):
            z = by_zone.setdefault(rd["zone"], {"temp": [], "rh": [], "ts": []})
            z["temp"].append(rd.get("temp_f"))
            z["rh"].append(rd.get("rh"))
            z["ts"].append(rep.get("generated_at"))

    zones_out = []
    excursions = []
    for zone in sorted(by_zone, key=_zone_sort_key):
        temp_band, rh_band = config.band_for_zone(zone)
        data = by_zone[zone]
        temp_stats = _stats(data["temp"])
        rh_stats = _stats(data["rh"])

        temp_ok = [_in_band(v, temp_band) for v in data["temp"]]
        rh_ok = [_in_band(v, rh_band) for v in data["rh"]]

        for i, ok in enumerate(temp_ok):
            if ok is False:
                excursions.append({"zone": zone, "metric": "temp",
                                   "value": data["temp"][i], "at": data["ts"][i],
                                   "band_lo": temp_band[0], "band_hi": temp_band[1]})
        for i, ok in enumerate(rh_ok):
            if ok is False:
                excursions.append({"zone": zone, "metric": "rh",
                                   "value": data["rh"][i], "at": data["ts"][i],
                                   "band_lo": rh_band[0], "band_hi": rh_band[1]})

        zones_out.append({
            "zone": zone,
            "samples": len(data["ts"]),
            "temp": temp_stats,
            "rh": rh_stats,
            "temp_band": list(temp_band),
            "rh_band": list(rh_band),
            "temp_adherence": _adherence(temp_ok),
            "rh_adherence": _adherence(rh_ok),
            # Intraday snapshot points for the sparklines (nulls kept for gaps).
            "temp_series": [{"at": t, "value": v}
                            for t, v in zip(data["ts"], data["temp"])],
            "rh_series": [{"at": t, "value": v}
                          for t, v in zip(data["ts"], data["rh"])],
            "in_band": (temp_ok[-1] is not False) and (rh_ok[-1] is not False)
            if temp_ok or rh_ok else None,
        })

    return {
        "date": date_str,
        "snapshot_count": len(reports),
        "generated_at_list": [r.get("generated_at") for r in reports],
        "zone_count": len(zones_out),
        "excursion_count": len(excursions),
        "zones": zones_out,
        "excursions": excursions,
    }


def all_dates(store: dict[str, Any]) -> list[str]:
    """Sorted unique calendar dates present in the store."""
    dates = {
        (r.get("generated_at") or "")[:10]
        for r in store.get("reports", []) if r.get("generated_at")
    }
    return sorted(d for d in dates if d)


def facility_of(store: dict[str, Any]) -> str:
    """First segment of the location path, e.g. 'Crystal Bridges Museum'."""
    for r in store.get("reports", []):
        path = r.get("location_path") or ""
        if path:
            return path.split("/")[0].strip()
    return "Gallery Conditions"


def build_dashboard(store: dict[str, Any]) -> dict[str, Any]:
    """Everything the static dashboard renders: facility, bands, all daily rollups."""
    dates = all_dates(store)
    return {
        "facility": facility_of(store),
        "temp_band": list(config.DEFAULT_TEMP_BAND),
        "rh_band": list(config.DEFAULT_RH_BAND),
        "dates": dates,
        "latest": dates[-1] if dates else None,
        "days": {d: daily_summary(store, d) for d in dates},
    }


def _adherence(flags: list[Optional[bool]]) -> Optional[float]:
    seen = [f for f in flags if f is not None]
    if not seen:
        return None
    return round(100.0 * sum(1 for f in seen if f) / len(seen), 1)


def _zone_sort_key(zone: str):
    # "AHU 13" -> (13,) so numeric AHUs sort naturally, not lexically.
    parts = zone.split()
    if len(parts) == 2 and parts[1].isdigit():
        return (0, int(parts[1]))
    return (1, zone)
