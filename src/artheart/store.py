"""Flat-file store for parsed reports (data/readings.json).

Deliberately dependency-free (no pdfplumber import) so it stays fast to test.
Takes plain dicts as produced by parser.Report.as_dict().
"""
from __future__ import annotations

import json
import os
from typing import Any

SCHEMA_VERSION = 1

# Keys we refuse to persist to the public repo (see DESIGN.md mitigations).
_DROP_KEYS = {"generated_by", "warnings"}


def empty_store() -> dict[str, Any]:
    return {"version": SCHEMA_VERSION, "reports": []}


def load_store(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return empty_store()
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_store(path: str, store: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(store, fh, indent=2, sort_keys=False)
        fh.write("\n")


def has_report(store: dict[str, Any], gmail_msg_id: str) -> bool:
    return any(r.get("gmail_msg_id") == gmail_msg_id for r in store["reports"])


def add_report(store: dict[str, Any], report_dict: dict[str, Any],
               gmail_msg_id: str, *, replace: bool = False) -> bool:
    """Append a parsed report. Returns False if already stored (unless replace).

    Drops person-identifying fields and renames title -> gallery_title. With
    replace=True, an existing report with the same message id is re-parsed in
    place (used to backfill after a parser fix).
    """
    existing = has_report(store, gmail_msg_id)
    if existing and not replace:
        return False
    clean = {k: v for k, v in report_dict.items() if k not in _DROP_KEYS}
    clean["gallery_title"] = clean.pop("title", None)
    clean["gmail_msg_id"] = gmail_msg_id
    if existing:
        store["reports"] = [clean if r.get("gmail_msg_id") == gmail_msg_id else r
                            for r in store["reports"]]
    else:
        store["reports"].append(clean)
    # Keep chronological by generation time when available.
    store["reports"].sort(key=lambda r: r.get("generated_at") or "")
    return True
