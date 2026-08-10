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

# --- Gmail ingest -------------------------------------------------------------
# Query that selects the report emails. TODO: confirm the real label/sender.
# Examples: 'subject:CBMAA has:attachment filename:pdf'
#           'from:webctrl@crystalbridges.org has:attachment'
GMAIL_QUERY = os.environ.get(
    "ARTHEART_GMAIL_QUERY", "has:attachment filename:pdf subject:CBMAA"
)
# Mailbox to read (service account impersonates this Workspace user).
GMAIL_USER = os.environ.get("ARTHEART_GMAIL_USER", "")

# --- Paths --------------------------------------------------------------------
DATA_FILE = os.environ.get("ARTHEART_DATA_FILE", "data/readings.json")
SITE_DATA_DIR = os.environ.get("ARTHEART_SITE_DATA", "site/data")

# --- Dashboard / email --------------------------------------------------------
DASHBOARD_URL = os.environ.get("ARTHEART_DASHBOARD_URL", "")


def band_for_zone(zone: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return ((temp_lo, temp_hi), (rh_lo, rh_hi)) for a zone, honoring overrides."""
    override = ZONE_BANDS.get(zone, {})
    return (
        override.get("temp", DEFAULT_TEMP_BAND),
        override.get("rh", DEFAULT_RH_BAND),
    )
