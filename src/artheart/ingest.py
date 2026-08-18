"""Email ingestion over IMAP — works with a personal Gmail + App Password.

No external dependencies (imaplib + email are stdlib) and no Google Cloud
project: enable 2-Step Verification on the mailbox, generate an App Password,
and set:

  ARTHEART_IMAP_USER      -- the mailbox address that receives the reports
  ARTHEART_IMAP_PASSWORD  -- a Gmail App Password (NOT the normal password)

Report emails are selected by sender + subject (config.REPORT_FROM /
REPORT_SUBJECT). PDFs are parsed in memory and NOT persisted to the repo;
dedup is by the email's Message-ID.
"""
from __future__ import annotations

import email
import imaplib
import os
import tempfile
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from typing import Any

from . import config
from .parser import parse_report


def _decode(raw: bytes | str | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "ignore")
    return str(make_header(decode_header(raw))).strip()


def _search_criteria() -> list[str]:
    crit = ["FROM", f'"{config.REPORT_FROM}"', "SUBJECT", f'"{config.REPORT_SUBJECT}"']
    if config.IMAP_SINCE_DAYS > 0:
        since = datetime.now(timezone.utc) - timedelta(days=config.IMAP_SINCE_DAYS)
        crit += ["SINCE", since.strftime("%d-%b-%Y")]
    return crit


def _pdf_attachments(msg: email.message.Message):
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = _decode(part.get_filename())
        ctype = part.get_content_type()
        if filename.lower().endswith(".pdf") or ctype == "application/pdf":
            payload = part.get_payload(decode=True)
            if payload:
                yield filename or "report.pdf", payload


def fetch_and_store(store_obj: dict[str, Any], *, user: str | None = None,
                    password: str | None = None, reprocess: bool = False) -> int:
    """Pull matching report emails, parse their PDFs, add to the store.

    Returns the number of newly added reports.
    """
    user = user or config.IMAP_USER
    password = password or os.environ.get("ARTHEART_IMAP_PASSWORD", "")
    if not user or not password:
        raise RuntimeError(
            "IMAP ingest needs ARTHEART_IMAP_USER and ARTHEART_IMAP_PASSWORD"
        )

    from .store import add_report, has_report  # keep store import-light

    added = 0
    M = imaplib.IMAP4_SSL(config.IMAP_HOST)
    try:
        M.login(user, password)
        mbox = config.IMAP_MAILBOX
        if " " in mbox and not mbox.startswith('"'):
            mbox = f'"{mbox}"'                      # quote e.g. "[Gmail]/All Mail"
        typ, _ = M.select(mbox, readonly=True)
        if typ != "OK":                             # fall back to INBOX if unavailable
            M.select("INBOX", readonly=True)
        typ, data = M.search(None, *_search_criteria())
        if typ != "OK":
            return 0
        for num in data[0].split():
            # Cheap dedup: peek only the Message-ID before downloading the body.
            typ, hdr = M.fetch(num, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            if typ != "OK" or not hdr or not hdr[0]:
                continue
            msg_id = _decode(email.message_from_bytes(hdr[0][1]).get("Message-ID")) \
                or num.decode()
            if has_report(store_obj, msg_id) and not reprocess:
                continue
            typ, raw = M.fetch(num, "(RFC822)")
            if typ != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            for _fname, pdf_bytes in _pdf_attachments(msg):
                with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
                    tf.write(pdf_bytes)
                    tf.flush()
                    report = parse_report(tf.name)
                if add_report(store_obj, report.as_dict(), msg_id, replace=reprocess):
                    added += 1
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return added
