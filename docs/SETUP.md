# Setup

One-time configuration to take artheart live. Code is done; these are the
account/secret steps only you can do.

## 1. Gmail access (IMAP + App Password — works with personal Gmail)

No Google Cloud project or Workspace admin needed. On the Google account that
**receives** the Gallery Heartbeat reports:

1. Turn on **2-Step Verification** (myaccount.google.com → Security). Required
   before App Passwords are available.
2. Create an **App Password** (myaccount.google.com → Security → App passwords).
   Name it `artheart`. Copy the 16-character password.
3. Make sure **IMAP is enabled** (Gmail → Settings → *Forwarding and POP/IMAP*
   → Enable IMAP).

The report filter is already baked in as defaults — sender
`cbmorspace@aweoffice.org`, subject `Gallery Heartbeat` — so there's nothing to
configure there.

## 2. GitHub repo configuration

**Settings → Pages:** Source = **GitHub Actions**.

**Settings → Secrets and variables → Actions**

Secrets:
| Name | Value |
|------|-------|
| `ARTHEART_IMAP_USER` | the mailbox that receives the reports, e.g. `you@gmail.com` |
| `ARTHEART_IMAP_PASSWORD` | the 16-char **App Password** from step 1 (not your login password) |

Variables:
| Name | Value |
|------|-------|
| `ARTHEART_DASHBOARD_URL` | the Pages URL, once known (e.g. `https://iridiumegg.github.io/artheart/`) |
| `ARTHEART_EMAIL_TO` | who gets the digest, comma-separated (defaults to the IMAP account) |
| `ARTHEART_EMAIL_FROM` | optional display sender; defaults to the IMAP account address |

> Optional overrides (defaults are correct for CBMAA): `ARTHEART_REPORT_FROM`,
> `ARTHEART_REPORT_SUBJECT`, `ARTHEART_IMAP_HOST`, `ARTHEART_IMAP_MAILBOX`.

## 2b. Email digest (Gmail SMTP — no extra service)

There is **nothing to set up** beyond the App Password above: the digest is sent
over Gmail SMTP using the same `ARTHEART_IMAP_PASSWORD`, from your Gmail account,
to `ARTHEART_EMAIL_TO` (or yourself by default). No Resend, no custom domain.

The digest sends automatically at ~6 PM Central. To test off-hours, run the
workflow manually with the repo/env variable `ARTHEART_FORCE_EMAIL=true`, or
run `ARTHEART_FORCE_EMAIL=true python -m artheart.pipeline` locally.

## 3. Run it

- **Actions → Gallery report sync → Run workflow** (manual), or just wait — it
  polls automatically.
- **Cadence:** the workflow polls the inbox **every ~15 min**. When a new report
  email is found it ingests it and **redeploys the dashboard** (runs with no new
  mail are no-ops and skip the deploy). The **email digest** still goes out
  **once per day at ~6 PM Central** (a per-day marker keeps the frequent polls
  from sending duplicates).
- A manual run always rebuilds and deploys; tick **force email** to also send
  the digest immediately.

> Note: pushing dashboard *code* changes (e.g. `site/index.html`) redeploys on
> the next run that ingests new data, or immediately via a manual run.

## Report filter (already configured)

- Sender: `cbmorspace@aweoffice.org`
- Subject contains: `Gallery Heartbeat`

Override via the `ARTHEART_REPORT_FROM` / `ARTHEART_REPORT_SUBJECT` variables if
the reports ever change address or subject.
