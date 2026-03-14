"""Eastmoney FinSkillsHub (CLAW) data fetcher implementation."""

import asyncio
import os
from typing import Any, List, Dict
import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseDataFetcher
from .exceptions import DataFetchError, DataNotFoundError, NetworkError
from src.config import get_settings

class ClawFetcher(BaseDataFetcher):
    """Data fetcher using official Eastmoney FinSkillsHub (CLAW) APIs."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.eastmoney_api_key
        self.base_url = "https://mkapi2.dfcfs.com/finskillshub/api/claw"
        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    async def _post(self, endpoint: str, payload: dict) -> dict:
        """Internal helper for POST requests to FinSkillsHub."""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") != 0 and result.get("status") != 100: # 100 sometimes used for business ok
                    raise DataFetchError(f"CLAW API Error: {result.get('message', 'Unknown error')}")
                
                return result.get("data", {})
        except httpx.HTTPError as e:
            raise NetworkError(f"Network error calling CLAW API: {str(e)}")
        except Exception as e:
            raise DataFetchError(f"Unexpected error in CLAW fetcher: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch_kline(self, stock_code: str, interval: str = "daily", limit: int = 200) -> pd.DataFrame:
        """Fetch K-line data - falling back to AkShare for raw history."""
        from .akshare_fetcher import AkShareFetcher
        return await AkShareFetcher().fetch_kline(stock_code, interval, limit)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch_financial_metrics(self, stock_code: str) -> dict:
        """Fetch core financial metrics via bulk-keyword stock-screen query."""
        # Use specific metric names as keywords to trigger detailed results
        keywords = ["净资产收益率", "净利润率", "营收增长率", "资产负债率", "流动比率", "现金分红比例", "市盈率", "市净率", "总市值", "销售毛利率", "归属母公司股东的净利润最新同比增长率", "研发费用(含资本化)"]
        bulk_kw = f"{stock_code} " + " ".join(keywords)
        
        payload = {
            "keyword": bulk_kw,
            "pageNo": 1,
            "pageSize": 1
        }
        data = await self._post("stock-screen", payload)
        result_inner = data.get("data", {}).get("result", {})
        items = result_inner.get("dataList", [])
        
        if not items:
            return {"error": f"未找到股票 {stock_code} 的核心财务数据。请确保代码正确。"}
        
        item = items[0]
        columns = result_inner.get("columns", [])
        metrics = {"_raw_source": "Eastmoney High-Fidelity Skill (Bulk)"}
        for col in columns:
            title = col.get("title")
            key = col.get("key")
            val = item.get(key)
            if val is not None:
                metrics[title] = val
        return metrics

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch_realtime_quote(self, stock_code: str) -> dict:
        """Fetch real-time quotes via CLAW stock-screen query."""
        payload = {
            "keyword": f"{stock_code} 实时行情",
            "pageNo": 1,
            "pageSize": 1
        }
        data = await self._post("stock-screen", payload)
        result_inner = data.get("data", {}).get("result", {})
        items = result_inner.get("dataList", [])
        if not items:
            return {"error": f"无法获取 {stock_code} 的实时行情。"}
        
        item = items[0]
        columns = result_inner.get("columns", [])
        quote = {"_raw_source": "Eastmoney Realtime"}
        for col in columns:
            key = col.get("key")
            title = col.get("title")
            if key in item:
                quote[title] = item[key]
        
        # Add common aliases for ease of use (checks both raw keys and mapped titles)
        quote["price"] = quote.get("最新价") or quote.get("最新价(元)") or item.get("NEW_PRICE")
        quote["changePercent"] = quote.get("涨跌幅") or quote.get("涨跌幅(%)") or item.get("CHANGE_RATE")
        quote["volume"] = quote.get("成交量") or quote.get("成交量(股)") or item.get("VOLUME")
        return quote

    async def fetch_stock_list(self, market: str | None = None) -> pd.DataFrame:
        """Uses Eastmoney screen skill to get stock lists."""
        payload = {
            "keyword": f"{market or 'A股'}全部股票",
            "pageNo": 1,
            "pageSize": 5000
        }
        data = await self._post("stock-screen", payload)
        result_inner = data.get("data", {}).get("result", {})
        df = pd.DataFrame(result_inner.get("dataList", []))
        return df

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch_news(self, stock_code: str, limit: int = 10) -> List[Dict]:
        """Fetch news via news-search skill using correct 'query' parameter."""
        payload = {
            "query": f"{stock_code}",
            "pageNo": 1,
            "pageSize": limit
        }
        # Endpoint news-search identified as working with 'query'
        data_outer = await self._post("news-search", payload)
        # news-search structure: data.data (the list)
        items = data_outer.get("data", [])
        news_list = []
        for item in items:
            news_list.append({
                "title": item.get("chunk", "")[:200],
                "content": item.get("chunk", ""),
                "date": item.get("id", ""),
                "source": "东方财富官方资讯"
            })
        if not news_list:
            news_list.append({"title": "暂无官方公开资讯", "content": "未搜索到相关新闻，请勿编造虚假信息。"})
        return news_list

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def fetch_technical_analysis(self, stock_code: str) -> dict:
        """Fetch technical indicators via bulk-keyword stock-screen query."""
        keywords = ["MA指标", "RSI指标", "MACD指标", "技术评价", "支撑位", "压力位", "资金排名"]
        bulk_kw = f"{stock_code} " + " ".join(keywords)
        
        payload = {
            "keyword": bulk_kw,
            "pageNo": 1,
            "pageSize": 1
        }
        data = await self._post("stock-screen", payload)
        result_inner = data.get("data", {}).get("result", {})
        items = result_inner.get("dataList", [])
        
        analysis = {
            "summary": "官方深度技术指标实时数据",
            "indicators": {},
            "_raw_source": "Eastmoney Tech Skill (Bulk)"
        }
        
        if items:
            item = items[0]
            columns = result_inner.get("columns", [])
            for col in columns:
                key = col.get("key")
                title = col.get("title")
                if key in item:
                    analysis["indicators"][title] = item[key]
            # Try to build a summary string if missing
            if "技术面评价" in analysis["indicators"]:
                analysis["summary"] = analysis["indicators"]["技术面评价"]
        else:
            analysis["summary"] = "警告：未找到官方技术指标。请确保代码正确且股票交易正常。"
                    
        return analysis
