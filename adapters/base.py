"""
Every source — API or scraper — implements this same interface.
Adding source #31 means writing one new class here, nothing else in
the pipeline changes.
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class SourceAdapter(ABC):
    #: unique, stable name used in logs, monitoring, and dedup source-priority rules
    source_name: str

    @abstractmethod
    def fetch_raw(self) -> List[Dict]:
        """
        Return a list of raw, source-specific dicts (untouched API/HTML output).
        Must raise on failure so the orchestrator can log/alert on that source
        without killing the whole run.
        """
        raise NotImplementedError

    @abstractmethod
    def to_events(self, raw_items: List[Dict]) -> List["Event"]:  # noqa: F821
        """Map this source's raw shape into the canonical Event model."""
        raise NotImplementedError

    def run(self):
        """Standard entry point the orchestrator calls for every adapter."""
        raw = self.fetch_raw()
        return self.to_events(raw)
