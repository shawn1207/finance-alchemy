"""KLine (K线) domain entities."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class KLineInterval(StrEnum):
    """K-line time interval."""

    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    MIN_60 = "60m"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class KLine(BaseModel):
    """Single K-line candlestick entity."""

    stock_code: str
    interval: KLineInterval
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal  # shares traded
    amount: Decimal  # turnover in CNY
    timestamp: datetime

    model_config = {"frozen": True}

    @field_validator("open", "high", "low", "close", "volume", "amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Price/volume fields must be non-negative")
        return v

    @field_validator("high")
    @classmethod
    def high_gte_low(cls, v: Decimal, info) -> Decimal:  # type: ignore[misc]
        low = info.data.get("low")
        if low is not None and v < low:
            raise ValueError("high must be >= low")
        return v


class KLineSeries(BaseModel):
    """Aggregate of ordered KLine records for a single stock/interval."""

    stock_code: str
    interval: KLineInterval
    bars: list[KLine] = Field(default_factory=list)

    model_config = {"frozen": False}

    def latest(self, n: int = 1) -> list[KLine]:
        """Return the n most-recent bars (sorted by timestamp desc)."""
        sorted_bars = sorted(self.bars, key=lambda b: b.timestamp, reverse=True)
        return sorted_bars[:n]

    def date_range(self, start: datetime, end: datetime) -> "KLineSeries":
        """Return a new KLineSeries filtered to [start, end] inclusive."""
        filtered = [b for b in self.bars if start <= b.timestamp <= end]
        return KLineSeries(
            stock_code=self.stock_code,
            interval=self.interval,
            bars=filtered,
        )

    def close_prices(self) -> list[Decimal]:
        """Return close prices in chronological order."""
        return [b.close for b in sorted(self.bars, key=lambda b: b.timestamp)]

    def volumes(self) -> list[Decimal]:
        """Return volumes in chronological order."""
        return [b.volume for b in sorted(self.bars, key=lambda b: b.timestamp)]

    def __len__(self) -> int:
        return len(self.bars)
