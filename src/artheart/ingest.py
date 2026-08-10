"""Gmail ingestion via a Workspace service account (domain-wide delegation).

Google libraries are imported lazily so the rest of the package (and its tests)
never require them. Credentials come from env:

  GOOGLE_SERVICE_ACCOUNT_JSON  -- the service-account key JSON (string)
  ARTHEART_GMAIL_USER          -- mailbox to read (impersonated)
  ARTHEART_GMAIL_QUERY         -- Gmail search selecting the report emails

Raw PDFs are parsed in a temp dir and NOT persisted to the public repo.
"""
from __future__ import annotations

import base64
import json
import os
import tempfile
from typing import Any

from . import config
from .parser import parse_report

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _service(sa_json: str, user: str):
    from google.oauth2 import service_account  # lazy
    from googleapiclient.discovery import build

    info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=GMAIL_SCOPES, subject=user
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _iter_pdf_attachments(svc, user: str, msg_id: str):
    """Yield (filename, bytes) for each PDF attachment on a message."""
    msg = svc.users().messages().get(userId=user, id=msg_id, format="full").execute()
    parts = list(msg.get("payload", {}).get("parts", []) or [])
    while parts:
        part = parts.pop()
        parts.extend(part.get("parts", []) or [])
        filename = part.get("filename") or ""
        if not filename.lower().endswith(".pdf"):
            continue
        body = part.get("body", {})
        att_id = body.get("attachmentId")
        if att_id:
            att = svc.users().messages().attachments().get(
                userId=user, messageId=msg_id, id=att_id
            ).execute()
            data = att.get("data", "")
        else:
            data = body.get("data", "")
        if data:
            yield filename, base64.urlsafe_b64decode(data)


def fetch_and_store(store_obj: dict[str, Any], *, sa_json: str | None = None,
                    user: str | None = None, query: str | None = None) -> int:
    """Pull new report emails, parse their PDFs, add to the store. Returns new count."""
    sa_json = sa_json or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    user = user or config.GMAIL_USER
    query = query or config.GMAIL_QUERY
    if not sa_json or not user:
        raise RuntimeError(
            "Gmail ingest needs GOOGLE_SERVICE_ACCOUNT_JSON and ARTHEART_GMAIL_USER"
        )

    from .store import add_report, has_report  # local import keeps store dep-free

    svc = _service(sa_json, user)
    added = 0
    page_token = None
    while True:
        resp = svc.users().messages().list(
            userId=user, q=query, pageToken=page_token, maxResults=100
        ).execute()
        for m in resp.get("messages", []):
            msg_id = m["id"]
            if has_report(store_obj, msg_id):
                continue
            for _fname, pdf_bytes in _iter_pdf_attachments(svc, user, msg_id):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tf:
                    tf.write(pdf_bytes)
                    tf.flush()
                    report = parse_report(tf.name)
                if add_report(store_obj, report.as_dict(), msg_id):
                    added += 1
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return added
