"""Provider-fetcher contract — Protocol + WindowSeed value type.

Each provider module (e.g. `fred_fetcher.py`) implements `ProviderFetcher` by
returning a `WindowSeed` per symbol. The orchestrator in `__init__.py`
depends only on this contract; provider identity exists solely as a key in
the dispatch map.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.registry import SymbolEntry


@dataclass(frozen=True)
class WindowSeed:
    """A bootstrap-time snapshot ready to be loaded into a `RollingWindow`."""
    values: list[float]
    last_update: datetime


class ProviderFetcher(Protocol):
    """Adapter that knows how to populate one symbol's rolling window."""

    async def fetch_window(self, entry: SymbolEntry) -> WindowSeed | None:
        """Return the seeded window for `entry`, or `None` to skip."""
        ...
