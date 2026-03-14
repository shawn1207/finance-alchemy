"""AkShare data fetcher implementation."""

import asyncio
import time
from functools import lru_cache
from typing import Any

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseDataFetcher
from .exceptions import DataFetchError, DataNotFoundError, NetworkError, RateLimitError
from .utils import rate_limit


class _TTLCache:
    """Simple dict-based TTL cache."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, ts = entry
        if time.time() - ts > self._ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time.time())


class AkShareFetcher(BaseDataFetcher):
    """Data fetcher backed by AkShare (免费A股数据源).

    All public methods are async; blocking AkShare calls are dispatched
    to a thread-pool executor to avoid blocking the event loop.
    """

    def __init__(self, cache_ttl_seconds: int = 300) -> None:
        self._cache = _TTLCache(ttl_seconds=cache_ttl_seconds)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_sync(fn, *args, **kwargs) -> Any:  # type: ignore[no-untyped-def]
        """Run a synchronous callable and return its result."""
        return fn(*args, **kwargs)

    async def _run_in_executor(self, fn, *args, **kwargs) -> Any:  # type: ignore[no-untyped-def]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @rate_limit(calls_per_second=2.0, label="akshare")
    async def get_stock_name(self, stock_code: str) -> str:
        """Get the stock name for a given code."""
        cache_key = f"name:{stock_code}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import akshare as ak
            df = await self._run_in_executor(ak.stock_individual_info_em, symbol=stock_code)
            if df is not None and not df.empty:
                # The EM info table has 'item' and 'value' columns
                name_row = df[df["item"] == "股票简称"]
                if not name_row.empty:
                    name = str(name_row.iloc[0]["value"])
                    self._cache.set(cache_key, name)
                    return name
            return "未知股票"
        except Exception:
            return "未知股票"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @rate_limit(calls_per_second=1.0, label="akshare")
    async def fetch_kline(
        self,
        stock_code: str,
        interval: str = "daily",
        limit: int = 200,
    ) -> pd.DataFrame:
        """Fetch K-line data via akshare.stock_zh_a_hist."""
        cache_key = f"kline:{stock_code}:{interval}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import akshare as ak  # type: ignore[import-untyped]

            period_map = {
                "daily": "daily",
                "weekly": "weekly",
                "monthly": "monthly",
                "1m": "1",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "60m": "60",
            }
            period = period_map.get(interval, "daily")

            df: pd.DataFrame = await self._run_in_executor(
                ak.stock_zh_a_hist,
                symbol=stock_code,
                period=period,
                adjust="qfq",
            )
            if df is None or df.empty:
                raise DataNotFoundError(f"No K-line data for {stock_code}")

            df = df.tail(limit).copy()
            df = df.rename(
                columns={
                    "日期": "timestamp",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df[["timestamp", "open", "high", "low", "close", "volume", "amount"]]
            self._cache.set(cache_key, df)
            return df

        except DataNotFoundError:
            raise
        except Exception as exc:
            raise NetworkError(f"AkShare kline fetch failed for {stock_code}: {exc}") from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @rate_limit(calls_per_second=1.0, label="akshare")
    async def fetch_financial_metrics(self, stock_code: str) -> dict:
        """Fetch financial indicators via akshare.stock_financial_analysis_indicator."""
        cache_key = f"fin:{stock_code}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import akshare as ak  # type: ignore[import-untyped]

            df: pd.DataFrame = await self._run_in_executor(
                ak.stock_financial_analysis_indicator,
                symbol=stock_code,
                start_year="2023",
            )
            if df is None or df.empty:
                raise DataNotFoundError(f"No financial data for {stock_code}")

            row = df.iloc[-1].to_dict()
            self._cache.set(cache_key, row)
            return row

        except DataNotFoundError:
            raise
        except Exception as exc:
            raise DataFetchError(
                f"Financial metrics fetch failed for {stock_code}: {exc}"
            ) from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @rate_limit(calls_per_second=1.0, label="akshare")
    async def fetch_realtime_quote(self, stock_code: str) -> dict:
        """Fetch real-time quote via akshare.stock_zh_a_spot_em."""
        try:
            import akshare as ak  # type: ignore[import-untyped]

            df: pd.DataFrame = await self._run_in_executor(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                raise DataNotFoundError("Real-time quote board is empty")

            row = df[df["代码"] == stock_code]
            if row.empty:
                raise DataNotFoundError(f"No real-time quote for {stock_code}")

            return row.iloc[0].to_dict()

        except DataNotFoundError:
            raise
        except Exception as exc:
            raise NetworkError(f"Real-time quote fetch failed for {stock_code}: {exc}") from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @rate_limit(calls_per_second=0.5, label="akshare")
    async def fetch_stock_list(self, market: str | None = None) -> pd.DataFrame:
        """Fetch all A-share stock codes and names."""
        cache_key = f"list:{market}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            import akshare as ak  # type: ignore[import-untyped]

            df: pd.DataFrame = await self._run_in_executor(ak.stock_info_a_code_name)
            if df is None or df.empty:
                raise DataFetchError("Stock list is empty")

            if market == "SH":
                df = df[df["code"].str.startswith(("60", "68"))]
            elif market == "SZ":
                df = df[df["code"].str.startswith(("00", "30"))]
            elif market == "BJ":
                df = df[df["code"].str.startswith(("83", "87", "43"))]

            self._cache.set(cache_key, df)
            return df

        except DataFetchError:
            raise
        except Exception as exc:
            raise NetworkError(f"Stock list fetch failed: {exc}") from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    @rate_limit(calls_per_second=1.0, label="akshare")
    async def fetch_news(self, stock_code: str, limit: int = 10) -> list[dict]:
        """Fetch recent news articles via akshare.stock_news_em."""
        try:
            import akshare as ak  # type: ignore[import-untyped]

            df: pd.DataFrame = await self._run_in_executor(
                ak.stock_news_em, symbol=stock_code
            )
            if df is None or df.empty:
                return []

            return df.head(limit).to_dict(orient="records")

        except Exception as exc:
            raise NetworkError(f"News fetch failed for {stock_code}: {exc}") from exc
