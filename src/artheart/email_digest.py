"""Phase 2: the 6 PM email digest.

Sends via the Resend HTTP API using only the stdlib (urllib) so there's no
extra dependency. Email is inline-styled table HTML for reliable rendering in
Gmail/Outlook. Configured via env:

  RESEND_API_KEY        -- Resend API key
  ARTHEART_EMAIL_FROM   -- verified sender, e.g. "artheart <reports@your.dom>"
  ARTHEART_EMAIL_TO     -- comma-separated recipients
  ARTHEART_DASHBOARD_URL-- link the button points at
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from . import config

RESEND_URL = "https://api.resend.com/emails"

# Palette (mirrors the dashboard).
_BG = "#0d1117"
_PANEL = "#161b22"
_LINE = "#232b36"
_INK = "#e6edf3"
_MUTED = "#8b98a5"
_TEAL = "#2dd4bf"
_BAD = "#ef4444"
_OK = "#22c55e"


def build_subject(summary: dict[str, Any]) -> str:
    n = summary.get("excursion_count", 0)
    tail = "all zones in band" if n == 0 else f"{n} excursion{'s' if n != 1 else ''}"
    return f"CBMAA Gallery Conditions — {summary.get('date','')} — {tail}"


def _fmt(v, unit=""):
    return "—" if v is None else f"{v}{unit}"


def _adh_color(pct):
    if pct is None:
        return _MUTED
    if pct >= 100:
        return _OK
    if pct >= 90:
        return _TEAL
    return _BAD


def build_html(summary: dict[str, Any], dashboard_url: str = "") -> str:
    date = summary.get("date", "")
    zc = summary.get("zone_count", 0)
    sc = summary.get("snapshot_count", 0)
    ec = summary.get("excursion_count", 0)

    def stat(label, value, color=_INK):
        return (
            f'<td align="center" style="padding:14px;background:{_PANEL};'
            f'border:1px solid {_LINE};border-radius:10px">'
            f'<div style="font-size:11px;letter-spacing:.6px;text-transform:uppercase;'
            f'color:{_MUTED};font-family:Arial,sans-serif">{label}</div>'
            f'<div style="font-size:28px;font-weight:700;color:{color};'
            f'font-family:Consolas,monospace;margin-top:4px">{value}</div></td>'
        )

    stats = (
        '<table role="presentation" width="100%" cellspacing="8" cellpadding="0"><tr>'
        + stat("Zones", zc)
        + stat("Snapshots", sc)
        + stat("Excursions", ec, _BAD if ec else _OK)
        + "</tr></table>"
    )

    # Excursions block.
    if ec:
        items = "".join(
            f'<div style="background:#1b1113;border:1px solid #3b1113;border-radius:8px;'
            f'padding:10px 12px;margin:6px 0;color:#fca5a5;'
            f'font-family:Consolas,monospace;font-size:13px">'
            f'&#9888; {e["zone"]} — {e["metric"].upper()} '
            f'{e["value"]}{"°F" if e["metric"]=="temp" else "%"} outside '
            f'{e["band_lo"]}–{e["band_hi"]}{"°F" if e["metric"]=="temp" else "%"}'
            f'{(" · " + e["at"]) if e.get("at") else ""}</div>'
            for e in summary.get("excursions", [])
        )
    else:
        items = (
            f'<div style="color:{_OK};font-family:Consolas,monospace;font-size:14px;'
            f'padding:8px 0">&#10003; All zones within band today.</div>'
        )

    # Zone rows.
    rows = ""
    for z in summary.get("zones", []):
        bad = z.get("in_band") is False
        name_color = _BAD if bad else _INK
        rows += (
            f'<tr>'
            f'<td style="padding:9px 8px;border-bottom:1px solid {_LINE};'
            f'font-family:Consolas,monospace;color:{name_color}">{z["zone"]}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid {_LINE};'
            f'font-family:Consolas,monospace;color:{_INK}">{_fmt(z["temp"]["latest"])}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid {_LINE};'
            f'font-family:Consolas,monospace;color:{_INK}">{_fmt(z["rh"]["latest"])}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid {_LINE};'
            f'font-family:Consolas,monospace;color:{_adh_color(z["temp_adherence"])}">'
            f'{_fmt(z["temp_adherence"],"%")}</td>'
            f'<td style="padding:9px 8px;border-bottom:1px solid {_LINE};'
            f'font-family:Consolas,monospace;color:{_adh_color(z["rh_adherence"])}">'
            f'{_fmt(z["rh_adherence"],"%")}</td>'
            f'</tr>'
        )
    ztable = (
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        f'style="border-collapse:collapse;font-size:13px">'
        f'<tr>'
        + "".join(
            f'<th align="left" style="padding:8px;color:{_MUTED};font-size:11px;'
            f'text-transform:uppercase;letter-spacing:.5px;'
            f'border-bottom:1px solid {_LINE};font-family:Arial,sans-serif">{h}</th>'
            for h in ("AHU", "Temp °F", "RH %", "Temp adh.", "RH adh.")
        )
        + "</tr>"
        + rows
        + "</table>"
    )

    button = ""
    if dashboard_url:
        button = (
            f'<div style="text-align:center;margin:26px 0 6px">'
            f'<a href="{dashboard_url}" style="background:{_TEAL};color:#04201c;'
            f'text-decoration:none;font-family:Arial,sans-serif;font-weight:700;'
            f'padding:12px 26px;border-radius:8px;display:inline-block">'
            f'View full dashboard &rarr;</a></div>'
        )

    return f"""<!doctype html><html><body style="margin:0;background:{_BG};padding:24px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0">
<tr><td align="center">
<table role="presentation" width="640" cellspacing="0" cellpadding="0"
       style="max-width:640px;width:100%">
  <tr><td style="padding:4px 4px 18px">
    <div style="font-size:22px;font-weight:700;color:{_INK};font-family:Arial,sans-serif">
      art<span style="color:{_TEAL}">heart</span>
      <span style="color:{_MUTED};font-weight:400;font-size:14px"> — Gallery Conditions</span>
    </div>
    <div style="color:{_MUTED};font-family:Consolas,monospace;font-size:13px;margin-top:4px">
      {date} · {sc} snapshot(s)</div>
  </td></tr>
  <tr><td style="padding:0 4px">{stats}</td></tr>
  <tr><td style="padding:22px 4px 4px">
    <div style="color:{_MUTED};font-size:12px;text-transform:uppercase;letter-spacing:.8px;
                font-family:Arial,sans-serif;border-bottom:1px solid {_LINE};padding-bottom:6px">
      Excursions (temp 68–72 °F · RH 45–55 %)</div>
    {items}
  </td></tr>
  <tr><td style="padding:22px 4px 4px">
    <div style="color:{_MUTED};font-size:12px;text-transform:uppercase;letter-spacing:.8px;
                font-family:Arial,sans-serif;border-bottom:1px solid {_LINE};padding-bottom:6px">
      Zones (by AHU)</div>
    {ztable}
  </td></tr>
  <tr><td>{button}</td></tr>
  <tr><td style="padding:20px 4px;color:{_MUTED};font-family:Consolas,monospace;
                 font-size:11px;text-align:center">
    artheart · CBMAA gallery-condition aggregator</td></tr>
</table>
</td></tr></table>
</body></html>"""


def send(summary: dict[str, Any], *, api_key: str | None = None,
         sender: str | None = None, to: str | None = None,
         dashboard_url: str | None = None) -> dict:
    """Send the digest via Resend. Raises on missing config or HTTP error."""
    api_key = api_key or os.environ.get("RESEND_API_KEY", "")
    sender = sender or config.EMAIL_FROM
    to = to or config.EMAIL_TO
    dashboard_url = dashboard_url if dashboard_url is not None else config.DASHBOARD_URL
    if not api_key or not sender or not to:
        raise RuntimeError(
            "email needs RESEND_API_KEY, ARTHEART_EMAIL_FROM, ARTHEART_EMAIL_TO"
        )

    payload = {
        "from": sender,
        "to": [addr.strip() for addr in to.split(",") if addr.strip()],
        "subject": build_subject(summary),
        "html": build_html(summary, dashboard_url),
    }
    req = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))
