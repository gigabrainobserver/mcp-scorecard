"""Abstract base for enrichers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Enricher(ABC):
    """Base class for data enrichers.

    Each enricher takes a list of server entries and returns a dict
    keyed by server name with enrichment data.
    """

    @abstractmethod
    async def enrich(self, servers: list[Any]) -> dict[str, Any]:
        ...
