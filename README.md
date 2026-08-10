# artheart

Daily aggregator for CBMAA gallery-condition reports. Intercepts the WebCTRL
snapshot PDFs emailed throughout the day, stores the readings, and publishes an
interactive ES2-branded dashboard with a 6 PM Central email digest.

See [DESIGN.md](DESIGN.md) for the full architecture and build phases.

## Status
- [x] WebCTRL PDF parser (validated against a real report)
- [x] Flat-file store (dedup + name scrubbing)
- [x] Daily aggregation + derived excursions
- [x] Gmail ingestor (service account) — needs credentials to run live
- [x] GitHub Actions workflow (schedule + Pages deploy)
- [x] Dashboard placeholder (reads summary.json)
- [x] 6 PM email digest (Resend, stdlib-only)
- [ ] Polished ES2 / Recharts dashboard (Phase 3)

See [docs/SETUP.md](docs/SETUP.md) for going live.

## Dev
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q

# parse a report
python -m artheart.parser tests/samples/CBMAA_Gallery_2_sample.pdf
# build site/data from the stored readings (ingest auto-skips without creds)
python -m artheart.pipeline
```
