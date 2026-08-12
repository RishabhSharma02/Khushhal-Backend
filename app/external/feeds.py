"""Climate + market feed protocols.

Phase-3 scaffolding — the default implementations return neutral values so
`insights_service` produces the same output as today. Swap in real IMD /
OpenWeather / Agmarknet clients later without touching the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ClimateSignal:
    """Rainfall deviation from norm over the trailing year, as % of normal."""
    rain_dev_yr_min: float  # -100..+100
    rain_dev_yr_max: float


@dataclass(frozen=True, slots=True)
class MarketSignal:
    """Rolling 3-month terms-of-trade change (+/- fraction)."""
    tot_chg_3m_min: float  # -1.0..+1.0


class ClimateFeed(Protocol):
    def signal_for(self, *, state: str | None, district: str | None) -> ClimateSignal: ...


class MarketFeed(Protocol):
    def signal_for(self, *, sector: str) -> MarketSignal: ...


class NeutralClimateFeed:
    """Zero-deviation baseline — same numbers the sector template ships with."""
    def signal_for(self, *, state: str | None, district: str | None) -> ClimateSignal:
        return ClimateSignal(rain_dev_yr_min=0.0, rain_dev_yr_max=0.0)


class NeutralMarketFeed:
    def signal_for(self, *, sector: str) -> MarketSignal:
        return MarketSignal(tot_chg_3m_min=0.0)


# Global registry — the insights service pulls from here. Replaced by real
# feeds by rebinding these names (e.g., from an app startup hook once
# credentials for IMD/Agmarknet are configured).
climate_feed: ClimateFeed = NeutralClimateFeed()
market_feed: MarketFeed = NeutralMarketFeed()
