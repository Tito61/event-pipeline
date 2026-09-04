"""
Canonical Event schema.

Every source adapter (API or scraper) must produce raw dicts that get
mapped into this ONE structure by the normalization layer. This is what
lets us add a 31st source without touching dedup, storage, or the API.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    source: str                    # e.g. "ticketmaster", "muze_izmir_scraper"
    source_id: str                 # the ID/URL from the source, for traceability
    name: str
    start_datetime: Optional[datetime]   # normalized to UTC
    timezone: Optional[str]              # original local timezone, kept for display
    venue: Optional[str]
    city: Optional[str]
    address: Optional[str]
    category: Optional[str]        # normalized via category map
    description: Optional[str]
    event_url: Optional[str]
    image_url: Optional[str]
    ticket_info: Optional[str]
    price_min: Optional[float]
    price_max: Optional[float]
    currency: Optional[str]
    lat: Optional[float] = None
    lon: Optional[float] = None
    raw_payload: dict = field(default_factory=dict)  # kept for debugging/audit

    def dedup_key_exact(self) -> str:
        """Cheap exact-match key: normalized name + venue + start time (to the minute)."""
        name = (self.name or "").strip().lower()
        venue = (self.venue or "").strip().lower()
        ts = self.start_datetime.strftime("%Y-%m-%dT%H:%M") if self.start_datetime else "unknown"
        return f"{name}|{venue}|{ts}"
