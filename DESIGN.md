# artheart — Daily Gallery Condition Aggregator

Intercept the WebCTRL gallery-condition report emails, aggregate the day's
readings, and publish a beautiful, chart-heavy **interactive dashboard** —
with a 6:00 PM Central email linking to it (headline stats + snapshot).

Owner: Nate Stewart (ES2). Facility: Crystal Bridges Museum of American Art (CBMAA).

---

## 1. What the reports actually are

Each email carries a **WebCTRL point-snapshot PDF**. Verified against a real
file (`tests/samples/CBMAA_Gallery_2_sample.pdf`):

```
CBMAA Gallery 2
Location: Crystal Bridges Museum / CBMAA Main / 2nd Floor / AHU 1
Location   Humidity                          Zone Temp
AHU 2      53.8 @ 08/10/2026 09:14:55 AM     69.0
AHU 4      48.7 @ 08/10/2026 11:00:00 AM     69.5
...
ES2 - Nate Stewart (nstewart)  08/10/2026 11:00:20 AM  Page 1 of 1
```

Facts that shape the whole design:

- **One report = one point-in-time snapshot** of a gallery. Row per served
  unit (AHU). Each row has **Humidity (value @ timestamp)** and **Zone Temp (°F)**.
- **Zone Temp can be blank** (e.g. AHU 19). Handle nulls, never assume a value.
- **~3 reports/day.** So ~3 datapoints per zone per day — sparse intraday.
  Value comes from **day-over-day / longer history** and **band adherence**,
  not fake-dense hourly curves.
- **No alarm/setpoint columns exist in the report.** Excursions are
  **derived** by comparing each reading to a per-zone target band (below).

## 2. Hierarchy & data model

**Each AHU is a gallery.** Label galleries by AHU number ("AHU 2", "AHU 13", …).
A single report lists every AHU; ~3 reports/day = the same set of AHUs sampled 3×.

```
Report (a snapshot: generated_at + all AHUs)
  └── Zone / Gallery (an AHU: "AHU 2")
        └── Reading (metric, value, ts) captured each snapshot
```

Postgres:

```sql
reports(id, gmail_msg_id UNIQUE, gallery_title, location_path,
        generated_at, generated_by, source_pdf_url, parse_confidence, ingested_at)
zones(id, gallery_title, name,                        -- e.g. "AHU 2"
      temp_lo, temp_hi, rh_lo, rh_hi)                 -- target band (configurable)
readings(id, report_id, zone_id, metric,              -- 'temp' | 'rh'
         reading_ts, value)                           -- time-series
excursions(id, zone_id, metric, reading_ts, value, band_lo, band_hi, severity)
```

`readings` is the time-series spine. `excursions` is derived on ingest and
recomputed if bands change.

### Target bands (derived-excursion thresholds)

Museum art-preservation defaults (tunable per zone in `zones`):

| Metric | Band       | Notes |
|--------|------------|-------|
| Temp   | 68–72 °F   | CBMAA target (confirmed) |
| RH     | 45–55 %    | CBMAA target (confirmed) |

Bands are stored per zone so any gallery can be tuned later; the values above
are the confirmed defaults. (In the sample report, AHU 13 at 72.2 °F is one
derived temp excursion.)

## 3. Architecture / data flow — GitHub-native

At this volume (7 AHUs × ~3/day ≈ 21 rows/day, ~8k/year) no database or paid
host is needed. Everything but the auth gate lives in GitHub.

```
Gmail (Workspace)                          GitHub repo
   PDF reports                     ┌───────────────────────────────┐
        │                          │  data/readings.json  (storage)│
        ▼                          │  data/pdfs/          (raw PDF) │
  GitHub Actions (scheduled) ──────┤  site/  (static dashboard src)│
   fetch → parse → append          └───────────────────────────────┘
        │  build → deploy → email                │ deploy
        ├────────────────────────▶ Email digest  ▼
        │   (Resend) link+stats    Cloudflare Pages + Access  ◀── me & staff
        │                          (or GitHub Pages)   gated, interactive
```

One Actions run ~18:15 America/Chicago: fetch the day's report emails → parse →
append to `readings.json` → rebuild the static dashboard → deploy → email digest.
Optional midday run keeps the page fresh earlier.

### Components

**1. Ingestion — Gmail → Actions**
- Google Workspace **service account with domain-wide delegation** (creds stored
  as an Actions secret) reads the target mailbox. No interactive OAuth to refresh.
- Scheduled workflow fetches messages matching a label/sender filter; a per-day
  run is enough given the ~3/day cadence (no tight polling needed).
- Dedup on `gmail_msg_id` so re-runs never double-count.

**2. PDF parser — DONE / validated** (`src/artheart/parser.py`)
- `pdfplumber` extracts the single table + header/footer text.
- Splits `"53.8 @ 08/10/2026 09:14:55 AM"` into value + timestamp; parses temp;
  tolerates blank cells; pulls title, location path, generated-at/by.
- Emits `parse_confidence` so bad parses surface instead of corrupting charts.
- Raw PDF archived into the repo (or a Release).

**3. Storage — a committed data file.** `data/readings.json` (or SQLite),
versioned in git — diffable, free, trivially backed up. Postgres only if history
outgrows a flat file (years away at this rate).

**4. Aggregator + dashboard — the "beautiful, chart-heavy" part**
- **Next.js + Recharts**, styled to the **ES2 dark tech aesthetic** (teal
  accents, Poppins/mono) per the `es2-design` + `dataviz` conventions.
- Stable per-day URLs: `/report/2026-08-10`. Because data is snapshot-sparse,
  lead with views that stay rich at 3 points/day:
  - **Band-adherence gauges** per zone (temp & RH vs target band, color-coded)
  - **Today's snapshots** as small multiples (the 3 samples per zone)
  - **Day-over-day sparklines** and trailing 7/30-day adherence %
  - **Excursion log** (derived) with severity
  - **Gallery heatmap** (zone × metric, green→red vs band)

**5. Email out — 18:15 America/Chicago**
- A step in the Actions run → send via **Resend** (or Postmark).
- Email = headline stats + **static snapshot image** of the key chart +
  **link to the live dashboard**. Useful at a glance, rich on click.

**6. Access — public GitHub Pages** (chosen)
- Repo is **public**; dashboard served by **GitHub Pages** — no auth layer.
- Two mitigations baked in since this is the museum's facility data:
  1. **Raw PDFs are NOT committed** to the public repo. They already live
     permanently in Gmail (the durable archive); the repo persists only the
     aggregated `data/readings.json`. (Add a private repo later if a redundant
     PDF archive is wanted.)
  2. **`generated_by` (person name) is dropped** on persist — the parser
     extracts it for logs but `store.add_report()` never writes it to JSON.

**7. Hosting.** GitHub Actions (compute/schedule) + GitHub repo (storage) +
GitHub Pages (public dashboard). Single platform, ~$0, near-zero ops.

## 4. Recommended stack

| Layer        | Choice |
|--------------|--------|
| Ingest/parse/aggregate/email | Python (pdfplumber, google-api-python-client, Resend) |
| Storage      | Committed `data/readings.json` in the repo (name-scrubbed) |
| Raw PDFs     | Left in Gmail (not committed to the public repo) |
| Dashboard    | Static GitHub Pages site, client-side interactive charts |
| Scheduler    | GitHub Actions scheduled workflow @ ~18:15 America/Chicago |
| Hosting      | GitHub Actions + repo + GitHub Pages (all public, ~$0) |

## 5. Build phases

1. **Ingest → parse → store** one report end-to-end (parser ✅; add Gmail +
   Postgres). Prove the data is clean.
2. **6 PM email** with headline stats + derived excursions (no dashboard yet).
   Daily value starts immediately.
3. **Interactive dashboard** with full ES2-branded charts.
4. **Polish:** push notifications, excursion alerting, multi-gallery rollups,
   long-range trends.

## 6. Decisions & open questions

Resolved:
- **AHU = gallery**, labeled by AHU number. One report lists all AHUs, ~3×/day.
- **Bands: 68–72 °F, 45–55 % RH.**
- **Hosting on GitHub** (Actions + repo data + static dashboard), gated via
  Cloudflare Pages/Access for "me and staff".

Still open:
1. **Cloudflare Pages + Access** acceptable for the auth gate, or is GitHub
   Enterprise Cloud (private Pages) already available? Which email domain(s)
   for the allowed users?
2. **Retention**: how long to keep raw PDFs and readings history? (git keeps
   everything by default — fine unless you want a cap.)
3. **Which Gmail label/sender/subject** identifies the report emails (for the
   ingest filter)?
