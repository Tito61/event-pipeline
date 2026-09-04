"""
Orchestrates a full daily run: fetch from every registered adapter,
normalize, deduplicate, store, and report per-source health.

In production this is what your scheduler (cron / Airflow / Prefect)
triggers once a day. Adding a new source = add one line to ADAPTERS.
"""
import json
import logging
from datetime import datetime

from adapters.ticketmaster_adapter import TicketmasterAdapter
from adapters.site_scraper_adapter import GenericSiteScraperAdapter
from normalize import normalize_events
from dedup import deduplicate
from storage import get_session, save_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("event_pipeline")

ADAPTERS = [
    TicketmasterAdapter(),          # demo_mode auto-enabled: no API key in this sandbox
    GenericSiteScraperAdapter(),    # demo_mode auto-enabled: no live_url in this sandbox
]


def run_pipeline():
    source_health = []
    all_events = []

    for adapter in ADAPTERS:
        start = datetime.utcnow()
        try:
            events = adapter.run()
            all_events.extend(events)
            source_health.append({
                "source": adapter.source_name,
                "status": "ok",
                "records": len(events),
                "duration_sec": (datetime.utcnow() - start).total_seconds(),
            })
            log.info(f"[{adapter.source_name}] fetched {len(events)} events")
        except Exception as exc:
            source_health.append({
                "source": adapter.source_name,
                "status": "failed",
                "error": str(exc),
                "duration_sec": (datetime.utcnow() - start).total_seconds(),
            })
            log.error(f"[{adapter.source_name}] FAILED: {exc}")
            # one bad source never kills the run for the others

    log.info(f"Total raw events collected: {len(all_events)}")

    normalized = normalize_events(all_events)
    deduped, merge_log = deduplicate(normalized)

    log.info(f"After dedup: {len(deduped)} unique events ({len(merge_log)} merges)")
    for kind, loser_source, loser_name, winner_source in merge_log:
        log.info(f"  [{kind} merge] '{loser_name}' from {loser_source} merged into {winner_source} record")

    session = get_session()
    save_events(session, deduped)
    log.info(f"Stored {len(deduped)} events to database")

    report = {
        "run_at": datetime.utcnow().isoformat(),
        "sources": source_health,
        "raw_count": len(all_events),
        "final_count": len(deduped),
        "merges": len(merge_log),
    }
    with open("last_run_report.json", "w") as f:
        json.dump(report, f, indent=2)

    return deduped, report


if __name__ == "__main__":
    events, report = run_pipeline()
    print("\n--- Sample of stored events ---")
    for e in events:
        print(f"- [{e.source}] {e.name} | {e.city} | {e.start_datetime} | {e.category} | {e.venue}")
    print("\n--- Run report ---")
    print(json.dumps(report, indent=2))
