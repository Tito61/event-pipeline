# Event Data Pipeline — Prototype

A working prototype of a multi-source event data collection pipeline:
API ingestion + web scraping → normalization → deduplication → structured
storage → error monitoring.

## What this demonstrates

- **Pluggable source adapters** (`adapters/base.py`) — a common interface so
  a new source is one new class, not a rebuild
- **Real API adapter** (`adapters/ticketmaster_adapter.py`) — written against
  the actual Ticketmaster Discovery API schema; runs live against the real
  API given an API key, or falls back to a saved sample response with the
  identical shape when no key is set (this repo's default, since it has no
  outbound network access)
- **Real scraper adapter** (`adapters/site_scraper_adapter.py`) — BeautifulSoup
  parsing against a saved HTML fixture; the same code parses a live page
  given a URL, HTML structure and selectors permitting
- **Normalization** (`normalize.py`) — category/city vocabulary mapped to one
  consistent taxonomy across sources
- **Two-layer deduplication** (`dedup.py`) — exact key match, then fuzzy
  name/venue/time matching for cross-source duplicates that don't share
  identical fields, with field-level merge (not drop) and a source-priority
  rule
- **Storage** (`storage.py`) — SQLAlchemy models, SQLite here for zero-setup
  local runs, schema is Postgres-compatible (swap the connection string for
  production)
- **Orchestration + monitoring** (`pipeline.py`) — runs every adapter,
  isolates per-source failures so one broken source doesn't kill the run,
  writes a `last_run_report.json` health report

## Honest note on scope

This was built to demonstrate the pipeline architecture, not as a record of
a completed client project. The Ticketmaster adapter is written against the
real API and will call it live once you set `TICKETMASTER_API_KEY`; the
scraper adapter will parse a real page once given a `live_url`. In this
sandboxed demo both fall back to realistic saved sample data so the full
pipeline — including the cross-source duplicate detection — runs and is
verifiable end to end.

## Run it

```bash
pip install -r requirements.txt
python3 pipeline.py
```

Look at `last_run_report.json` after a run for per-source status.

## What changes for production

- Point `TicketmasterAdapter` at a real key, add adapters for the client's
  other 10–30 sources
- Swap SQLite for Postgres (`get_session("postgresql://...")`)
- Replace the cron-style `if __name__ == "__main__"` trigger with
  Airflow/Prefect for retries, alerting (Slack/email), and a dashboard
  over `source_health`
- Swap `difflib` fuzzy matching for `rapidfuzz` (faster) and add geospatial
  proximity as a second dedup signal once venues have reliable coordinates
- Add an API layer (FastAPI) over the `events` table for downstream delivery
