# artheart

Daily aggregator for CBMAA gallery-condition reports. Intercepts the WebCTRL
snapshot PDFs emailed throughout the day, stores the readings, and publishes an
interactive ES2-branded dashboard with a 6 PM Central email digest.

See [DESIGN.md](DESIGN.md) for the full architecture and build phases.

## Status
- [x] WebCTRL PDF parser (validated against a real report)
- [ ] Gmail ingestion
- [ ] Postgres storage
- [ ] 6 PM email digest
- [ ] Interactive dashboard

## Dev
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m artheart.parser tests/samples/CBMAA_Gallery_2_sample.pdf
```
