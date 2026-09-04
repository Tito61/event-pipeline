"""
Generic scraper adapter pattern for sources with no API.

In production this would fetch a live URL with requests/Playwright.
For this sandboxed demo it parses a saved local HTML file with the exact
same BeautifulSoup logic — swap `fetch_raw` to pull a live URL and
nothing else in the class changes.

Note this sample page intentionally includes an event ("Istanbul Jazz
Night - Autumn Session") that is the SAME real-world event as one already
returned by the Ticketmaster adapter, but with a slightly different title
and venue name — this is exactly the duplicate-across-sources problem
the pipeline needs to catch, and it's here on purpose to prove the
dedup logic works, not an accident.
"""
import os
from datetime import datetime
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

from adapters.base import SourceAdapter
from models import Event

SAMPLE_FILE = os.path.join(os.path.dirname(__file__), "..", "sample_data", "venue_events.html")


class GenericSiteScraperAdapter(SourceAdapter):
    source_name = "istanbulevents_scraper"

    def __init__(self, live_url: str = None, demo_mode: bool = None):
        self.live_url = live_url
        self.demo_mode = demo_mode if demo_mode is not None else not bool(live_url)

    def fetch_raw(self) -> List[Dict]:
        if self.demo_mode:
            with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            resp = requests.get(self.live_url, timeout=15, headers={"User-Agent": "EventPipelineBot/1.0"})
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        raw_items = []
        for card in soup.select(".event-card"):
            def text_of(selector):
                el = card.select_one(selector)
                return el.get_text(strip=True) if el else None

            link_el = card.select_one(".event-link")
            img_el = card.select_one(".event-image")

            raw_items.append({
                "title": text_of(".event-title"),
                "date": text_of(".event-date"),
                "time": text_of(".event-time"),
                "venue": text_of(".event-venue"),
                "city": text_of(".event-city"),
                "address": text_of(".event-address"),
                "category": text_of(".event-category"),
                "description": text_of(".event-desc"),
                "url": link_el.get("href") if link_el else None,
                "image_url": img_el.get("src") if img_el else None,
                "price_text": text_of(".event-price"),
            })
        return raw_items

    def to_events(self, raw_items: List[Dict]) -> List[Event]:
        events = []
        for item in raw_items:
            start_dt = None
            if item.get("date"):
                try:
                    time_part = item.get("time") or "00:00"
                    start_dt = datetime.strptime(f"{item['date']}T{time_part}", "%Y-%m-%dT%H:%M")
                except ValueError:
                    start_dt = None

            price_min = None
            price_text = (item.get("price_text") or "").lower()
            if "free" in price_text:
                price_min = 0.0
            else:
                digits = "".join(c for c in price_text if c.isdigit())
                price_min = float(digits) if digits else None

            events.append(Event(
                source=self.source_name,
                source_id=item.get("url") or item.get("title", ""),
                name=(item.get("title") or "").strip(),
                start_datetime=start_dt,
                timezone="Europe/Istanbul",
                venue=item.get("venue"),
                city=item.get("city"),
                address=item.get("address"),
                category=item.get("category"),
                description=item.get("description"),
                event_url=item.get("url"),
                image_url=item.get("image_url"),
                ticket_info=item.get("price_text"),
                price_min=price_min,
                price_max=None,
                currency="TRY" if item.get("city") in ("Istanbul", "Ankara", "Izmir") else None,
                raw_payload=item,
            ))
        return events
