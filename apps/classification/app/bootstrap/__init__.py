"""Bootstrap package — populates rolling windows at startup.

The orchestrator (`populate_windows`) iterates the registry and dispatches
each verified symbol to the provider fetcher registered for its
`bootstrap.provider`. Provider identity exists only as a key in
`_FETCHERS`; orchestrator code never branches on it.
"""
import logging
from collections import deque

from app.bootstrap.fred_fetcher import FredFetcher
from app.bootstrap.provider_fetcher import ProviderFetcher, WindowSeed
from app.config import registry
from app.registry import Provider
from app.state import RollingWindow, state

logger = logging.getLogger(__name__)

# Strategy registry — one entry per supported provider. Adding a new
# provider is exactly: implement `ProviderFetcher`, register it here.
_FETCHERS: dict[Provider, ProviderFetcher] = {
    "fred": FredFetcher(),
}


async def populate_windows() -> None:
    """Bootstrap every verified symbol declared in the registry."""
    logger.info("Bootstrap starting — populating rolling windows from registry...")
    for entry in registry.symbols.values():
        if entry.bootstrap is None:
            logger.warning(
                "Skipping bootstrap for %s — no bootstrap spec in registry",
                entry.symbol,
            )
            continue
        if not entry.bootstrap.verified:
            logger.warning(
                "Skipping bootstrap for %s — not yet verified (verified: false in registry)",
                entry.symbol,
            )
            continue
        fetcher = _FETCHERS.get(entry.bootstrap.provider)
        if fetcher is None:
            logger.warning(
                "%s: bootstrap provider %r not implemented yet — skipping",
                entry.symbol, entry.bootstrap.provider,
            )
            continue
        seed = await fetcher.fetch_window(entry)
        if seed is None:
            continue
        state.windows[entry.symbol] = RollingWindow(
            indicator_class=entry.indicator_class,
            values=deque(seed.values, maxlen=entry.indicator_class.N),
            last_update=seed.last_update,
        )
    state.is_ready = True
    logger.info(
        "Bootstrap complete — service is ready (%d windows).",
        len(state.windows),
    )


__all__ = ["ProviderFetcher", "WindowSeed", "populate_windows"]
