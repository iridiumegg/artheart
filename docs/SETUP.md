# Setup

One-time configuration to take artheart live. Code is done; these are the
account/secret steps only you can do.

## 1. Gmail access (service account, domain-wide delegation)

1. In **Google Cloud Console**, create (or reuse) a project → enable the
   **Gmail API** → create a **Service Account** → create a **JSON key**.
2. Note the service account's **Client ID**.
3. In **Google Workspace Admin** → *Security → API controls → Domain-wide
   delegation* → **Add new**:
   - Client ID: the service account's client ID
   - Scope: `https://www.googleapis.com/auth/gmail.readonly`
4. The account impersonates the mailbox that receives the reports
   (`ARTHEART_GMAIL_USER`).

> Why a service account and not OAuth: it runs unattended forever with no
> token-refresh step to break.

## 2. GitHub repo configuration

**Settings → Pages:** Source = **GitHub Actions**.

**Settings → Secrets and variables → Actions**

Secrets:
| Name | Value |
|------|-------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | full contents of the service-account JSON key |
| `ARTHEART_GMAIL_USER` | mailbox that receives the reports, e.g. `reports@…` |
| `RESEND_API_KEY` | (Phase 2) transactional-email key for the digest |

Variables:
| Name | Value |
|------|-------|
| `ARTHEART_GMAIL_QUERY` | Gmail search that selects report emails — **TODO confirm**, e.g. `subject:CBMAA has:attachment filename:pdf` |
| `ARTHEART_DASHBOARD_URL` | the Pages URL, once known (e.g. `https://iridiumegg.github.io/artheart/`) |
| `ARTHEART_EMAIL_FROM` | verified Resend sender, e.g. `artheart <reports@yourdomain.com>` |
| `ARTHEART_EMAIL_TO` | recipient(s), comma-separated, e.g. `nstewart@es2built.com` |

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

## Still to confirm

- **`ARTHEART_GMAIL_QUERY`** — the exact label/sender/subject on the report
  emails so the ingestor grabs only those.
