"""
In-memory application state — rolling windows and readiness flag.

This module only holds the data structures. Bootstrap logic lives in main.py.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from app.config import registry
from app.registry import IndicatorClass, UnknownSymbolError


@dataclass
class RollingWindow:
    """Rolling window of float values with last-update tracking.

    Carries a reference to its indicator class so consumers can read
    calibration parameters (N, D, deviation_kind, expected_frequency_seconds)
    without a second registry lookup. The deque is sized from `indicator_class.N`
    at construction (or via __post_init__ when a pre-populated deque is passed).
    """
    indicator_class: IndicatorClass
    values: deque[float] = field(default_factory=deque)
    last_update: datetime | None = None

    def __post_init__(self) -> None:
        # Ensure the deque is sized from the class. Callers may pass an
        # un-bounded or differently-bounded deque (e.g. tests, bootstrap
        # pre-population); we resize it here so N is honoured uniformly
        # regardless of construction site.
        if self.values.maxlen != self.indicator_class.N:
            self.values = deque(self.values, maxlen=self.indicator_class.N)

    def append(self, value: float, timestamp: datetime) -> None:
        self.values.append(value)
        self.last_update = timestamp


@dataclass
class AppState:
    # Single window store keyed by symbol. Replaces the per-strategy dicts:
    # MARKET_DATA / MACROECONOMIC / CROSS_ASSET_FLOW now share one map because
    # the registry-driven model treats every symbol uniformly. Deviation
    # computation (per indicator_class.deviation_kind) is what differs, not
    # storage.
    windows: dict[str, RollingWindow] = field(default_factory=dict)

    # Readiness: False until all windows have been bootstrapped from APIs.
    # The /health endpoint exposes this.
    is_ready: bool = False

    def get_or_create_window(self, symbol: str) -> RollingWindow:
        """Resolve or create a rolling window for `symbol`.

        Raises UnknownSymbolError if the symbol is not in the registry —
        strategy layer catches this and returns a CLS-009 degraded response.
        """
        existing = self.windows.get(symbol)
        if existing is not None:
            return existing
        entry = registry.get_symbol(symbol)  # raises UnknownSymbolError
        window = RollingWindow(indicator_class=entry.indicator_class)
        self.windows[symbol] = window
        return window


# The singleton instance. Import and mutate this directly from anywhere in the app.
state = AppState()


# Re-export so strategy code can `from app.state import UnknownSymbolError`
# without reaching into app.registry (keeps the "state is the boundary" feel).
__all__ = ["AppState", "RollingWindow", "UnknownSymbolError", "state"]
