"""End-to-end pipeline entrypoint, run by the GitHub Actions workflow.

  python -m artheart.pipeline

Steps:
  1. ingest new report emails into data/readings.json (skipped if no creds)
  2. write the aggregated day summaries the dashboard reads (site/data/*)
  3. optionally email the digest (only near SEND_HOUR local time)

Designed to be idempotent: safe to run several times a day.
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
    if do_ingest and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") and config.GMAIL_USER:
        from . import ingest
        added = ingest.fetch_and_store(data)
        store.save_store(config.DATA_FILE, data)
        print(f"ingest: added {added} new report(s)")
    else:
        print("ingest: skipped (no Gmail credentials configured)")

    today = _today_local()
    summary = aggregate.daily_summary(data, today)

    os.makedirs(config.SITE_DATA_DIR, exist_ok=True)
    _write_json(os.path.join(config.SITE_DATA_DIR, "summary.json"), summary)
    shutil.copyfile(config.DATA_FILE, os.path.join(config.SITE_DATA_DIR, "readings.json")) \
        if os.path.exists(config.DATA_FILE) else None
    print(f"summary: {today} -> {summary['snapshot_count']} snapshot(s), "
          f"{summary['zone_count']} zone(s), {summary['excursion_count']} excursion(s)")

    # Email digest around 6pm local (or forced for a manual test run).
    should_email = os.environ.get("RESEND_API_KEY") and (
        config.FORCE_EMAIL or _local_hour() == config.SEND_HOUR
    )
    if should_email:
        try:
            from . import email_digest
            email_digest.send(summary)
            print("email: digest sent")
        except Exception as exc:  # never let email failure fail the build
            print(f"email: skipped ({exc})")
    else:
        print("email: not this run (outside send hour / no key)")

    return summary


def _write_json(path: str, obj) -> None:
    import json
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    run()
