"""
Normalization pass applied after every adapter produces Events, before
dedup/storage. Keeps category and city vocabulary consistent across
sources that each spell things differently.
"""
from typing import List
from models import Event

CATEGORY_MAP = {
    "jazz": "Music",
    "electronic": "Music",
    "music": "Music",
    "food & drink": "Food & Drink",
    "film": "Film & Cinema",
    "art": "Art & Culture",
    "miscellaneous": "Other",
}

CITY_MAP = {
    "istanbul": "Istanbul",
    "ankara": "Ankara",
    "izmir": "Izmir",
    "london": "London",
    "paris": "Paris",
    "munich": "Munich",
    "münchen": "Munich",
}


def normalize_events(events: List[Event]) -> List[Event]:
    for e in events:
        if e.category:
            e.category = CATEGORY_MAP.get(e.category.strip().lower(), e.category.strip().title())
        if e.city:
            e.city = CITY_MAP.get(e.city.strip().lower(), e.city.strip().title())
        if e.name:
            e.name = " ".join(e.name.split())  # collapse stray whitespace
    return events
