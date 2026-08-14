"""End-to-end pipeline entrypoint, run by the GitHub Actions workflow.

  python -m artheart.pipeline

Steps:
  1. ingest new report emails into data/readings.json (skipped if no creds)
  2. write the aggregated day summaries the dashboard reads (site/data/*)
  3. email the digest once per day at/after SEND_HOUR local time

Designed to be idempotent: safe to run every few minutes. The dashboard updates
whenever new data arrives; the email is sent at most once per calendar day.
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

from . import aggregate, config, store


def _today_local() -> str:
    return datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d")


def _local_hour() -> int:
    return datetime.now(ZoneInfo(config.TIMEZONE)).hour


def run(*, do_ingest: bool = True) -> dict:
    data = store.load_store(config.DATA_FILE)

    added = 0
    if do_ingest and config.IMAP_USER and os.environ.get("ARTHEART_IMAP_PASSWORD"):
        try:
            from . import ingest
            added = ingest.fetch_and_store(data)
            if added:
                store.save_store(config.DATA_FILE, data)
            print(f"ingest: added {added} new report(s)")
        except Exception as exc:  # transient IMAP hiccup must not fail the poll
            print(f"ingest: error, keeping existing data ({exc})")
    else:
        print("ingest: skipped (no IMAP credentials configured)")

    # Summarize the latest day that actually has data (falls back to today).
    # Reports may arrive across the day, or a run may fire before the day's
    # reports land — either way the digest should show the most recent readings.
    dates = aggregate.all_dates(data)
    today = _today_local()
    report_date = today if today in dates else (dates[-1] if dates else today)
    summary = aggregate.daily_summary(data, report_date)

    os.makedirs(config.SITE_DATA_DIR, exist_ok=True)
    _write_json(os.path.join(config.SITE_DATA_DIR, "summary.json"), summary)
    _write_json(os.path.join(config.SITE_DATA_DIR, "dashboard.json"),
                aggregate.build_dashboard(data))
    if os.path.exists(config.DATA_FILE):
        shutil.copyfile(config.DATA_FILE,
                        os.path.join(config.SITE_DATA_DIR, "readings.json"))
    print(f"summary: {report_date} -> {summary['snapshot_count']} snapshot(s), "
          f"{summary['zone_count']} zone(s), {summary['excursion_count']} excursion(s)")

    # Email digest: a 6am recap of the PREVIOUS day. The live dashboard keeps
    # showing today's data as it arrives, but the morning email summarizes the
    # most recent day before today (so it's yesterday's complete 7am-9pm span,
    # and stays yesterday's even if the 6am run is delayed past the 7am report).
    # Sent once per day (per-day marker); FORCE_EMAIL bypasses without consuming
    # the day's slot.
    smtp_pw = os.environ.get("ARTHEART_SMTP_PASSWORD") or os.environ.get("ARTHEART_IMAP_PASSWORD")
    already_sent = _email_marker() == today
    due = _local_hour() >= config.SEND_HOUR and not already_sent
    if smtp_pw and config.EMAIL_TO and (config.FORCE_EMAIL or due):
        prior = [d for d in dates if d < today]
        email_date = prior[-1] if prior else report_date
        email_summary = summary if email_date == report_date else \
            aggregate.daily_summary(data, email_date)
        try:
            from . import email_digest
            email_digest.send(email_summary)
            if not config.FORCE_EMAIL:
                _write_email_marker(today)
            print(f"email: digest sent (recap of {email_date})")
        except Exception as exc:  # never let email failure fail the run
            print(f"email: skipped ({exc})")
    else:
        print("email: not due" if not already_sent else "email: already sent today")

    return summary


def _email_marker() -> str:
    try:
        with open(config.EMAIL_MARKER, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _write_email_marker(date_str: str) -> None:
    os.makedirs(os.path.dirname(config.EMAIL_MARKER) or ".", exist_ok=True)
    with open(config.EMAIL_MARKER, "w", encoding="utf-8") as fh:
        fh.write(date_str + "\n")


def _write_json(path: str, obj) -> None:
    import json
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    run()
