"""Integration tests for AkShare data fetcher.

These tests require network access and a working AkShare installation.
They are skipped by default. Run with: pytest -m integration -s
"""

import pytest


@pytest.mark.skip(reason="Requires network access and AkShare")
class TestAkShareFetcher:
    async def test_fetch_kline_returns_dataframe(self):
        from src.infrastructure.data_fetcher.akshare_fetcher import AkShareFetcher
        fetcher = AkShareFetcher()
        df = await fetcher.fetch_kline("000001", "daily", 50)
        assert not df.empty
        assert "close" in df.columns
        assert len(df) <= 50

    async def test_fetch_realtime_quote(self):
        from src.infrastructure.data_fetcher.akshare_fetcher import AkShareFetcher
        fetcher = AkShareFetcher()
        quote = await fetcher.fetch_realtime_quote("000001")
        assert isinstance(quote, dict)
        assert len(quote) > 0

    async def test_fetch_stock_list(self):
        from src.infrastructure.data_fetcher.akshare_fetcher import AkShareFetcher
        fetcher = AkShareFetcher()
        df = await fetcher.fetch_stock_list()
        assert not df.empty
        assert len(df) > 100
