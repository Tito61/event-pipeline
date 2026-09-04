"""
Ticketmaster Discovery API adapter.

This is a REAL adapter — point it at the live API with an API key and it
works unmodified. For this demo (sandboxed, no outbound internet access
to Ticketmaster), it falls back to a saved sample response with the exact
same schema Ticketmaster returns, so the normalization/dedup/storage code
downstream is exercised end-to-end and honestly.

Docs: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
"""
import json
import os
from datetime import datetime
from typing import List, Dict

import requests

from adapters.base import SourceAdapter
from models import Event

SAMPLE_FILE = os.path.join(os.path.dirname(__file__), "..", "sample_data", "ticketmaster_sample.json")


class TicketmasterAdapter(SourceAdapter):
    source_name = "ticketmaster"

    def __init__(self, api_key: str = None, cities: List[str] = None, demo_mode: bool = None):
        self.api_key = api_key or os.environ.get("TICKETMASTER_API_KEY")
        self.cities = cities or ["Istanbul", "Ankara", "Izmir", "London", "Paris", "Munich"]
        # Auto demo mode if no key was supplied — makes the script runnable out of the box
        self.demo_mode = demo_mode if demo_mode is not None else not bool(self.api_key)

    def fetch_raw(self) -> List[Dict]:
        if self.demo_mode:
            with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("_embedded", {}).get("events", [])

        # --- Real live call path ---
        all_events = []
        base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
        for city in self.cities:
            resp = requests.get(base_url, params={
                "apikey": self.api_key,
                "city": city,
                "size": 100,
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            all_events.extend(data.get("_embedded", {}).get("events", []))
        return all_events

    def to_events(self, raw_items: List[Dict]) -> List[Event]:
        events = []
        for item in raw_items:
            venue_data = (item.get("_embedded", {}).get("venues") or [{}])[0]
            classification = (item.get("classifications") or [{}])[0]
            price_range = (item.get("priceRanges") or [{}])[0]
            image = (item.get("images") or [{}])[0]

            start = item.get("dates", {}).get("start", {})
            local_date = start.get("localDate")
            local_time = start.get("localTime", "00:00:00")
            start_dt = None
            if local_date:
                try:
                    start_dt = datetime.strptime(f"{local_date}T{local_time}", "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    start_dt = None

            location = venue_data.get("location", {})

            events.append(Event(
                source=self.source_name,
                source_id=item.get("id", ""),
                name=item.get("name", "").strip(),
                start_datetime=start_dt,
                timezone=item.get("dates", {}).get("timezone"),
                venue=venue_data.get("name"),
                city=venue_data.get("city", {}).get("name"),
                address=venue_data.get("address", {}).get("line1"),
                category=classification.get("genre", {}).get("name") or classification.get("segment", {}).get("name"),
                description=item.get("info"),
                event_url=item.get("url"),
                image_url=image.get("url"),
                ticket_info="Tickets via Ticketmaster" if item.get("url") else None,
                price_min=price_range.get("min"),
                price_max=price_range.get("max"),
                currency=price_range.get("currency"),
                lat=float(location["latitude"]) if location.get("latitude") else None,
                lon=float(location["longitude"]) if location.get("longitude") else None,
                raw_payload=item,
            ))
        return events
