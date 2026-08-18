"""Phase 2: the 6 PM email digest.

Sends over Gmail SMTP with the stdlib (smtplib) — the SAME App Password used for
IMAP ingest, so there's no second service, no custom domain, and no extra
dependency. Email is inline-styled table HTML for reliable rendering in Gmail.
Configured via env (all default sensibly to the IMAP account):

  ARTHEART_IMAP_PASSWORD  -- the Gmail App Password (reused for SMTP auth)
  ARTHEART_EMAIL_FROM     -- sender; defaults to the IMAP account address
  ARTHEART_EMAIL_TO       -- comma-separated recipients; defaults to the account
  ARTHEART_DASHBOARD_URL  -- link the button points at
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from . import config

# ES2 palette. Solid colors only (email clients drop rgba); every panel also
# carries a bgcolor="" attribute so Gmail can't strip the dark background.
_BG = "#0b1120"
_CARD = "#111d35"
_TILE = "#16243f"
_LINE = "#22314d"
_INK = "#ffffff"
_SEC = "#8baec8"
_MUTED = "#5b7590"
_TEAL = "#3dd6c8"
_BAD = "#e05656"
_OK = "#3dd6c8"


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
    sc = summary.get("snapshot_count", 0)
    ec = summary.get("excursion_count", 0)
    zc = summary.get("zone_count", 0)

    def stat(label, value, color=_INK):
        return (
            f'<td align="center" width="33%" bgcolor="{_TILE}" '
            f'style="background:{_TILE};padding:16px 8px;border:1px solid {_LINE};'
            f'border-radius:10px">'
            f'<div style="font-size:11px;letter-spacing:.6px;text-transform:uppercase;'
            f'color:{_SEC};font-family:Arial,Helvetica,sans-serif">{label}</div>'
            f'<div style="font-size:30px;font-weight:700;color:{color};'
            f'font-family:Consolas,\'Courier New\',monospace;padding-top:6px">{value}</div></td>'
        )

    stats = (
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">'
        f'<tr>{stat("Zones", zc)}<td width="12"></td>{stat("Snapshots", sc)}'
        f'<td width="12"></td>{stat("Excursions", ec, _BAD if ec else _OK)}</tr></table>'
    )

    if ec:
        items = "".join(
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin:6px 0"><tr><td bgcolor="#2a1416" '
            f'style="background:#2a1416;border:1px solid #4a2326;border-radius:8px;'
            f'padding:10px 12px;color:#f3b0b0;font-family:Consolas,monospace;font-size:13px">'
            f'&#9888; {e["zone"]} — {e["metric"].upper()} '
            f'{e["value"]}{"°F" if e["metric"]=="temp" else "%"} outside '
            f'{e["band_lo"]}–{e["band_hi"]}{"°F" if e["metric"]=="temp" else "%"}'
            f'{(" · " + e["at"].replace("T"," ")) if e.get("at") else ""}</td></tr></table>'
            for e in summary.get("excursions", [])
        )
    else:
        items = (
            f'<div style="color:{_OK};font-family:Consolas,monospace;font-size:14px;'
            f'padding:10px 0">&#10003; All zones within band.</div>'
        )

    rows = ""
    for z in summary.get("zones", []):
        bad = z.get("in_band") is False
        cell = f'padding:9px 8px;border-bottom:1px solid {_LINE};font-family:Consolas,monospace;'
        rows += (
            f'<tr>'
            f'<td style="{cell}color:{_BAD if bad else _INK}">{z["zone"]}</td>'
            f'<td style="{cell}color:{_INK}">{_fmt(z["temp"]["latest"])}</td>'
            f'<td style="{cell}color:{_INK}">{_fmt(z["rh"]["latest"])}</td>'
            f'<td style="{cell}color:{_adh_color(z["temp_adherence"])}">{_fmt(z["temp_adherence"],"%")}</td>'
            f'<td style="{cell}color:{_adh_color(z["rh_adherence"])}">{_fmt(z["rh_adherence"],"%")}</td>'
            f'</tr>'
        )
    ztable = (
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        f'style="border-collapse:collapse;font-size:13px"><tr>'
        + "".join(
            f'<th align="left" style="padding:8px;color:{_MUTED};font-size:11px;'
            f'text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid {_LINE};'
            f'font-family:Arial,Helvetica,sans-serif">{h}</th>'
            for h in ("AHU", "Temp °F", "RH %", "Temp adh.", "RH adh.")
        )
        + "</tr>" + rows + "</table>"
    )

    def section(title):
        return (
            f'<div style="color:{_SEC};font-size:12px;text-transform:uppercase;'
            f'letter-spacing:.8px;font-family:Arial,Helvetica,sans-serif;'
            f'border-bottom:1px solid {_LINE};padding-bottom:6px;margin-bottom:6px">{title}</div>'
        )

    button = ""
    if dashboard_url:
        button = (
            f'<table role="presentation" cellspacing="0" cellpadding="0" style="margin:6px auto">'
            f'<tr><td bgcolor="{_TEAL}" style="background:{_TEAL};border-radius:8px">'
            f'<a href="{dashboard_url}" style="display:inline-block;padding:12px 28px;'
            f'color:#04201c;text-decoration:none;font-weight:700;'
            f'font-family:Arial,Helvetica,sans-serif;font-size:14px">'
            f'View full dashboard &rarr;</a></td></tr></table>'
        )

    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<style>:root{{color-scheme:dark;}} body{{margin:0;background:{_BG};}}</style>
</head>
<body bgcolor="{_BG}" style="margin:0;background:{_BG};">
<table role="presentation" width="100%" bgcolor="{_BG}" cellspacing="0" cellpadding="0"
       style="background:{_BG}"><tr>
<td align="center" style="padding:24px 16px">
  <table role="presentation" width="600" bgcolor="{_CARD}" cellspacing="0" cellpadding="0"
         style="max-width:600px;width:100%;background:{_CARD};border:1px solid {_LINE};border-radius:12px">
    <tr><td style="padding:22px 22px 10px">
      <div style="font-size:24px;font-weight:800;color:{_INK};font-family:Arial,Helvetica,sans-serif">
        art<span style="color:{_TEAL}">heart</span></div>
      <div style="color:{_SEC};font-family:Arial,Helvetica,sans-serif;font-size:13px;padding-top:2px">
        Gallery Conditions</div>
      <div style="color:{_MUTED};font-family:Consolas,monospace;font-size:13px;padding-top:8px">
        {date} &nbsp;·&nbsp; {sc} snapshot(s)</div>
    </td></tr>
    <tr><td style="padding:6px 18px 4px">{stats}</td></tr>
    <tr><td style="padding:20px 22px 4px">{section("Excursions (temp 68–72 °F · RH 45–55 %)")}{items}</td></tr>
    <tr><td style="padding:16px 22px 4px">{section("Zones (by AHU)")}{ztable}</td></tr>
    <tr><td style="padding:18px 22px 6px">{button}</td></tr>
    <tr><td style="padding:14px 22px 22px;color:{_MUTED};font-family:Consolas,monospace;
                   font-size:11px;text-align:center">
      artheart · CBMAA gallery-condition aggregator</td></tr>
  </table>
</td></tr></table>
</body></html>"""


def _plain_text(summary: dict[str, Any], dashboard_url: str) -> str:
    lines = [build_subject(summary), ""]
    for e in summary.get("excursions", []):
        u = "°F" if e["metric"] == "temp" else "%"
        lines.append(f"! {e['zone']} {e['metric'].upper()} {e['value']}{u} "
                     f"outside {e['band_lo']}-{e['band_hi']}{u}")
    if not summary.get("excursions"):
        lines.append("All zones within band.")
    if dashboard_url:
        lines += ["", f"Dashboard: {dashboard_url}"]
    return "\n".join(lines)


def _dispatch(subject: str, html: str, text: str, *, to: str | None = None,
              password: str | None = None, sender: str | None = None) -> None:
    """Send one multipart (plain+HTML) email over Gmail SMTP."""
    password = password or os.environ.get("ARTHEART_SMTP_PASSWORD") \
        or os.environ.get("ARTHEART_IMAP_PASSWORD", "")
    sender = sender or config.EMAIL_FROM or config.SMTP_USER
    to = to or config.EMAIL_TO or config.SMTP_USER
    if not password or not config.SMTP_USER or not to:
        raise RuntimeError(
            "email needs ARTHEART_IMAP_USER, ARTHEART_IMAP_PASSWORD, ARTHEART_EMAIL_TO"
        )
    recipients = [a.strip() for a in to.split(",") if a.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
        s.starttls()
        s.login(config.SMTP_USER, password)
        s.sendmail(sender, recipients, msg.as_string())


def send(summary: dict[str, Any], *, password: str | None = None,
         sender: str | None = None, to: str | None = None,
         dashboard_url: str | None = None) -> None:
    """Send the daily digest over Gmail SMTP. Raises on missing config or SMTP error."""
    dashboard_url = dashboard_url if dashboard_url is not None else config.DASHBOARD_URL
    _dispatch(build_subject(summary),
              build_html(summary, dashboard_url),
              _plain_text(summary, dashboard_url),
              to=to, password=password, sender=sender)


# --- Real-time excursion alert ------------------------------------------------
def _unit(metric: str) -> str:
    return "°F" if metric == "temp" else "%"


def build_alert_subject(excursions: list[dict]) -> str:
    if len(excursions) == 1:
        e = excursions[0]
        return (f"Gallery excursion — {e['zone']} "
                f"{e['metric'].upper()} {e['value']}{_unit(e['metric'])}")
    return f"{len(excursions)} gallery excursions — CBMAA"


def _alert_plain(excursions: list[dict], dashboard_url: str) -> str:
    lines = ["Galleries out of band:", ""]
    for e in excursions:
        u = _unit(e["metric"])
        side = "over" if e["value"] > e["band_hi"] else "under"
        lines.append(f"! {e['zone']} — {e['metric'].upper()} {e['value']}{u} "
                     f"({abs(e['delta'])}{u} {side} {e['band_lo']}-{e['band_hi']}{u})"
                     + (f" at {e['at'].replace('T',' ')}" if e.get('at') else ""))
    if dashboard_url:
        lines += ["", f"Dashboard: {dashboard_url}"]
    return "\n".join(lines)


def build_alert_html(excursions: list[dict], dashboard_url: str = "") -> str:
    cards = ""
    for e in excursions:
        u = _unit(e["metric"])
        side = "over" if e["value"] > e["band_hi"] else "under"
        cards += (
            f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            f'style="margin:8px 0"><tr><td bgcolor="#2a1416" '
            f'style="background:#2a1416;border:1px solid #4a2326;border-radius:10px;padding:14px">'
            f'<table role="presentation" width="100%"><tr>'
            f'<td style="font-family:Consolas,monospace;color:#fca5a5;font-size:14px;font-weight:bold">'
            f'{e["zone"]}<div style="color:{_SEC};font-weight:normal;font-size:12px;padding-top:3px">'
            f'{e["metric"].upper()}'
            f'{(" · " + e["at"].replace("T"," ")) if e.get("at") else ""}</div></td>'
            f'<td align="right" style="font-family:Consolas,monospace">'
            f'<div style="color:{_BAD};font-size:22px;font-weight:bold">{e["value"]}{u}</div>'
            f'<div style="color:#f3b0b0;font-size:11px">{abs(e["delta"])}{u} {side} '
            f'{e["band_lo"]}–{e["band_hi"]}{u}</div></td>'
            f'</tr></table></td></tr></table>'
        )
    button = ""
    if dashboard_url:
        button = (
            f'<table role="presentation" cellspacing="0" cellpadding="0" style="margin:8px auto">'
            f'<tr><td bgcolor="{_TEAL}" style="background:{_TEAL};border-radius:8px">'
            f'<a href="{dashboard_url}" style="display:inline-block;padding:12px 28px;color:#04201c;'
            f'text-decoration:none;font-weight:700;font-family:Arial,Helvetica,sans-serif;font-size:14px">'
            f'View dashboard &rarr;</a></td></tr></table>'
        )
    heading = ("A gallery has left its condition band"
               if len(excursions) == 1 else
               f"{len(excursions)} galleries have left their condition band")
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="color-scheme" content="dark">
<style>:root{{color-scheme:dark;}} body{{margin:0;background:{_BG};}}</style></head>
<body bgcolor="{_BG}" style="margin:0;background:{_BG}">
<table role="presentation" width="100%" bgcolor="{_BG}" cellspacing="0" cellpadding="0" style="background:{_BG}">
<tr><td align="center" style="padding:24px 16px">
  <table role="presentation" width="600" bgcolor="{_CARD}" cellspacing="0" cellpadding="0"
         style="max-width:600px;width:100%;background:{_CARD};border:1px solid {_LINE};border-radius:12px">
    <tr><td style="padding:20px 22px 6px">
      <div style="font-size:24px;font-weight:800;color:{_INK};font-family:Arial,Helvetica,sans-serif">
        art<span style="color:{_TEAL}">heart</span></div>
      <div style="color:{_BAD};font-family:Consolas,monospace;font-size:13px;padding-top:4px">
        &#9888; Real-time condition alert</div>
      <div style="color:{_SEC};font-family:Arial,Helvetica,sans-serif;font-size:13px;padding-top:6px">
        {heading} (68–72 °F · 45–55 % RH).</div>
    </td></tr>
    <tr><td style="padding:6px 18px 4px">{cards}</td></tr>
    <tr><td style="padding:10px 22px 6px">{button}</td></tr>
    <tr><td style="padding:12px 22px 22px;color:{_MUTED};font-family:Consolas,monospace;font-size:11px;text-align:center">
      artheart · one alert per excursion, plus the 6 AM recap</td></tr>
  </table>
</td></tr></table></body></html>"""


def send_alert(excursions: list[dict], *, dashboard_url: str | None = None,
               to: str | None = None) -> None:
    """Send a real-time excursion alert over Gmail SMTP."""
    dashboard_url = dashboard_url if dashboard_url is not None else config.DASHBOARD_URL
    _dispatch(build_alert_subject(excursions),
              build_alert_html(excursions, dashboard_url),
              _alert_plain(excursions, dashboard_url),
              to=to or config.ALERT_TO)
