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
| `RESEND_API_KEY` | transactional-email key for the 6 PM digest |

Variables:
| Name | Value |
|------|-------|
| `ARTHEART_DASHBOARD_URL` | the Pages URL, once known (e.g. `https://iridiumegg.github.io/artheart/`) |
| `ARTHEART_EMAIL_FROM` | verified Resend sender, e.g. `artheart <reports@yourdomain.com>` |
| `ARTHEART_EMAIL_TO` | recipient(s), comma-separated, e.g. `nstewart@es2built.com` |

> Optional overrides (defaults are correct for CBMAA): `ARTHEART_REPORT_FROM`,
> `ARTHEART_REPORT_SUBJECT`, `ARTHEART_IMAP_HOST`, `ARTHEART_IMAP_MAILBOX`.

## 2b. Email digest (Resend)

1. Create a **Resend** account and **verify a sending domain** (add the DNS
   records Resend gives you). Free tier is plenty for one daily email.
2. Create an API key → store as the `RESEND_API_KEY` secret.
3. Set `ARTHEART_EMAIL_FROM` / `ARTHEART_EMAIL_TO` variables above.

The digest sends automatically at ~6 PM Central. To test off-hours, run the
workflow manually with the repo/env variable `ARTHEART_FORCE_EMAIL=true`, or
run `ARTHEART_FORCE_EMAIL=true python -m artheart.pipeline` locally.

## 3. Run it

- **Actions → Daily gallery report → Run workflow** (manual), or wait for the
  ~6:15 PM Central schedule.
- The run ingests new report emails, updates `data/readings.json`, rebuilds
  `site/`, and deploys Pages.

## Report filter (already configured)

- Sender: `cbmorspace@aweoffice.org`
- Subject contains: `Gallery Heartbeat`

Override via the `ARTHEART_REPORT_FROM` / `ARTHEART_REPORT_SUBJECT` variables if
the reports ever change address or subject.
