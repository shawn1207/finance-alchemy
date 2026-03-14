"""Abstract base class for data fetchers."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseDataFetcher(ABC):
    """Abstract interface for A-share market data sources."""

    @abstractmethod
    async def fetch_kline(
        self,
        stock_code: str,
        interval: str,
        limit: int = 200,
    ) -> pd.DataFrame:
        """Fetch K-line (OHLCV) data.

        Returns DataFrame with columns: [open, high, low, close, volume, amount, timestamp].
        """
        ...

    @abstractmethod
    async def fetch_financial_metrics(self, stock_code: str) -> dict:
        """Fetch latest financial metrics for a stock."""
        ...

    @abstractmethod
    async def fetch_realtime_quote(self, stock_code: str) -> dict:
        """Fetch real-time quote snapshot."""
        ...

    @abstractmethod
    async def fetch_stock_list(self, market: str | None = None) -> pd.DataFrame:
        """Fetch list of all A-share stocks, optionally filtered by market."""
        ...

    @abstractmethod
    async def fetch_news(self, stock_code: str, limit: int = 10) -> list[dict]:
        """Fetch recent news articles for a stock."""
        ...
