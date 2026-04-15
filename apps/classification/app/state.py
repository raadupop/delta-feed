"""
In-memory application state — rolling windows and readiness flag.

This module only holds the data structures. Bootstrap logic lives in main.py.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RollingWindow:
    """Rolling window of float values with last-update tracking."""
    values: deque[float]
    last_update: datetime | None = None

    def append(self, value: float, timestamp: datetime) -> None:
        self.values.append(value)
        self.last_update = timestamp


@dataclass
class AppState:
    # MARKET_DATA: per-symbol rolling window of last 20 daily closes.
    # Keys: e.g. "VIX", "OVX". Each deque has maxlen=20.
    market_data_history: dict[str, RollingWindow] = field(default_factory=dict)

    # MACROECONOMIC: last ~30 surprise magnitudes (|actual-expected|) per indicator
    # key = indicator name e.g. "CPI_YOY"
    macro_surprise_histories: dict[str, RollingWindow] = field(default_factory=dict)

    # CROSS_ASSET_FLOW: last 60 daily closes per ticker
    # key = ticker e.g. "SPY"
    cross_asset_windows: dict[str, RollingWindow] = field(default_factory=dict)

    # Readiness: False until all windows have been bootstrapped from APIs.
    # The /health endpoint exposes this.
    is_ready: bool = False


# The singleton instance. Import and mutate this directly from anywhere in the app.
state = AppState()
