"""Configuration for the artheart pipeline. Env vars override defaults."""
from __future__ import annotations

import os

# --- Scheduling ---------------------------------------------------------------
TIMEZONE = os.environ.get("ARTHEART_TZ", "America/Chicago")
SEND_HOUR = int(os.environ.get("ARTHEART_SEND_HOUR", "18"))  # local hour to email

# --- Condition target bands ---------------------------------------------------
DEFAULT_TEMP_BAND = (68.0, 72.0)   # deg F  (CBMAA confirmed)
DEFAULT_RH_BAND = (45.0, 55.0)     # % RH   (CBMAA confirmed)

# Per-zone overrides, e.g. {"AHU 8": {"temp": (67, 71)}}. Empty = use defaults.
ZONE_BANDS: dict[str, dict[str, tuple[float, float]]] = {}

# --- Email ingest (IMAP; works with personal Gmail + an App Password) ---------
IMAP_HOST = os.environ.get("ARTHEART_IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.environ.get("ARTHEART_IMAP_USER", "")        # mailbox that receives reports
IMAP_MAILBOX = os.environ.get("ARTHEART_IMAP_MAILBOX", "INBOX")
# Report emails are matched by sender + subject substring (confirmed values).
REPORT_FROM = os.environ.get("ARTHEART_REPORT_FROM", "cbmorspace@aweoffice.org")
REPORT_SUBJECT = os.environ.get("ARTHEART_REPORT_SUBJECT", "Gallery Heartbeat")
# Optional lookback bound; 0 = search all matching mail (dedup prevents rework).
IMAP_SINCE_DAYS = int(os.environ.get("ARTHEART_IMAP_SINCE_DAYS", "0"))

# --- Paths --------------------------------------------------------------------
DATA_FILE = os.environ.get("ARTHEART_DATA_FILE", "data/readings.json")
SITE_DATA_DIR = os.environ.get("ARTHEART_SITE_DATA", "site/data")

# --- Dashboard / email (Gmail SMTP; reuses the IMAP App Password) --------------
DASHBOARD_URL = os.environ.get(
    "ARTHEART_DASHBOARD_URL", "https://iridiumegg.github.io/artheart/"
)
SMTP_HOST = os.environ.get("ARTHEART_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("ARTHEART_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("ARTHEART_SMTP_USER", "") or IMAP_USER
EMAIL_FROM = os.environ.get("ARTHEART_EMAIL_FROM", "") or IMAP_USER  # default: send from self
EMAIL_TO = os.environ.get("ARTHEART_EMAIL_TO", "") or IMAP_USER      # default: to self
# Bypass the "only at SEND_HOUR" guard (for manual test runs).
FORCE_EMAIL = os.environ.get("ARTHEART_FORCE_EMAIL", "").lower() in ("1", "true", "yes")


def band_for_zone(zone: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return ((temp_lo, temp_hi), (rh_lo, rh_hi)) for a zone, honoring overrides."""
    override = ZONE_BANDS.get(zone, {})
    return (
        override.get("temp", DEFAULT_TEMP_BAND),
        override.get("rh", DEFAULT_RH_BAND),
    )
