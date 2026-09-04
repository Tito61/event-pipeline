"""
Two-layer duplicate detection.

Layer 1 (exact): hash of normalized name + venue + start-time-to-the-minute.
Catches the common case cheaply.

Layer 2 (fuzzy): for events that don't share an exact key but are
plausibly the same real-world event — same city, start time within a
tolerance window, and high name/venue text similarity. This is what
catches "Istanbul Jazz Nights: Autumn Session" (Ticketmaster) vs.
"Istanbul Jazz Night - Autumn Session" (scraper) even though the exact
key differs.

When two Events are judged duplicates, they are MERGED rather than one
being silently dropped — a SOURCE_PRIORITY order decides which source's
fields win for each field, but the richer non-empty value is kept
wherever the higher-priority source is missing that field.
"""
from difflib import SequenceMatcher
from datetime import timedelta
from typing import List
from models import Event

# Prefer official API data for core facts; scrapers often have richer descriptions/images
SOURCE_PRIORITY = ["ticketmaster"]  # anything not listed falls back after these, in encounter order

TIME_TOLERANCE = timedelta(minutes=90)
NAME_SIMILARITY_THRESHOLD = 0.72


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _is_probable_duplicate(a: Event, b: Event) -> bool:
    if not a.city or not b.city or a.city != b.city:
        return False
    if a.start_datetime and b.start_datetime:
        if abs(a.start_datetime - b.start_datetime) > TIME_TOLERANCE:
            return False
    elif a.start_datetime != b.start_datetime:
        return False  # one has a date and the other doesn't — too risky to merge

    name_sim = _similarity(a.name, b.name)
    venue_sim = _similarity(a.venue or "", b.venue or "")
    return name_sim >= NAME_SIMILARITY_THRESHOLD or (name_sim >= 0.5 and venue_sim >= 0.6)


def _priority_of(source: str) -> int:
    return SOURCE_PRIORITY.index(source) if source in SOURCE_PRIORITY else len(SOURCE_PRIORITY)


def _merge(primary: Event, secondary: Event) -> Event:
    """Fill any blank field on `primary` from `secondary`. `primary` wins on conflicts."""
    for field_name in primary.__dataclass_fields__:
        if field_name in ("raw_payload", "source", "source_id"):
            continue
        if getattr(primary, field_name) in (None, "", []):
            setattr(primary, field_name, getattr(secondary, field_name))
    return primary


def deduplicate(events: List[Event]) -> List[Event]:
    seen_exact = {}
    stage1: List[Event] = []
    merge_log = []

    for e in events:
        key = e.dedup_key_exact()
        if key in seen_exact:
            existing = seen_exact[key]
            winner, loser = (existing, e) if _priority_of(existing.source) <= _priority_of(e.source) else (e, existing)
            merged = _merge(winner, loser)
            seen_exact[key] = merged
            merge_log.append(("exact", loser.source, loser.name, winner.source))
        else:
            seen_exact[key] = e
            stage1.append(e)

    # Rebuild stage1 in case dict mutated in place
    stage1 = list(seen_exact.values())

    # Fuzzy pass over what's left
    final: List[Event] = []
    consumed = [False] * len(stage1)
    for i, a in enumerate(stage1):
        if consumed[i]:
            continue
        for j in range(i + 1, len(stage1)):
            if consumed[j]:
                continue
            b = stage1[j]
            if _is_probable_duplicate(a, b):
                winner, loser = (a, b) if _priority_of(a.source) <= _priority_of(b.source) else (b, a)
                winner = _merge(winner, loser)
                consumed[j] = True
                merge_log.append(("fuzzy", loser.source, loser.name, winner.source))
                a = winner
        final.append(a)

    return final, merge_log
