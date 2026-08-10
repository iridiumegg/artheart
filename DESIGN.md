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

```
Gallery (a report: title + location path)
  └── Zone (an AHU: "AHU 2")
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

| Metric | Default band | Notes |
|--------|--------------|-------|
| Temp   | 68–74 °F     | AAM/ASHRAE museum guidance, adjust per gallery |
| RH     | 45–55 %      | Tight band protects mixed-media collections |

Set real bands per zone before launch — Nate to confirm CBMAA's actual envelopes.

## 3. Architecture / data flow

```
Gmail (Workspace) ─(poll ~10m)─▶ Ingestor ─▶ PDF Parser ─▶ Postgres
   PDF reports                       │                         │
                                     └─▶ Object storage        │
                                         (raw PDFs)            ▼
              18:00 America/Chicago cron ─▶ Aggregator ─▶ Dashboard (web)
                                                │              ▲
                                                └─▶ Email out ─┘
                                                    link + snapshot + stats
```

### Components

**1. Ingestion — Gmail → app**
- Google Workspace **service account with domain-wide delegation** reads the
  target mailbox. Avoids interactive OAuth token-refresh failure that kills
  unattended services.
- **Poll every ~10 min** for messages matching a label/sender filter. Upgrade
  to **Gmail push (watch → Pub/Sub)** later for near-real-time.
- Dedup on `gmail_msg_id` so re-runs never double-count.

**2. PDF parser — DONE / validated** (`src/artheart/parser.py`)
- `pdfplumber` extracts the single table + header/footer text.
- Splits `"53.8 @ 08/10/2026 09:14:55 AM"` into value + timestamp; parses temp;
  tolerates blank cells; pulls title, location path, generated-at/by.
- Emits `parse_confidence` so bad parses surface instead of corrupting charts.
- Raw PDF archived to object storage.

**3. Storage — Postgres.** Plain Postgres is ample at this volume; add
TimescaleDB only if history grows large.

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

**5. Email out — 18:00 America/Chicago**
- Platform cron → aggregate the day → send via **Resend** (or Postmark).
- Email = headline stats + **static snapshot image** of the key chart +
  **link to the live dashboard**. Useful at a glance, rich on click.

**6. Access control — "me and staff"**
- Data isn't public. **Google SSO restricted to the CBMAA/ES2 domain** for the
  dashboard; email links carry a signed token. Decide before launch.

**7. Hosting.** One platform — **Render** or **Railway** (web service +
managed Postgres + cron in one place, minimal ops). Fly.io if more control wanted.

## 4. Recommended stack

| Layer        | Choice |
|--------------|--------|
| Ingest/parse/aggregate/email | Python (pdfplumber, google-api-python-client, Resend) |
| Storage      | Postgres |
| Object store | S3-compatible (raw PDFs) |
| Dashboard    | Next.js + Recharts, ES2 dark theme |
| Scheduler    | Platform cron @ 18:00 America/Chicago |
| Hosting      | Render or Railway |

## 5. Build phases

1. **Ingest → parse → store** one report end-to-end (parser ✅; add Gmail +
   Postgres). Prove the data is clean.
2. **6 PM email** with headline stats + derived excursions (no dashboard yet).
   Daily value starts immediately.
3. **Interactive dashboard** with full ES2-branded charts.
4. **Polish:** push notifications, excursion alerting, multi-gallery rollups,
   long-range trends.

## 6. Open questions

1. **3 reports/day = 3 galleries once each, or one gallery 3×/day?**
   (Sets whether the dashboard's primary axis is *gallery* or *time-of-day*.)
2. **Real target bands per gallery/zone** (defaults above are placeholders).
3. **Dashboard access**: Google SSO domain-restricted OK? Which domain(s)?
4. **Retention**: how long to keep raw PDFs and readings history?
