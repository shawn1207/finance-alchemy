"""CrewAI tool for Eastmoney Financial Search (Official API) with fallback logic."""

import json
import httpx
import re
import asyncio
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from src.config import get_settings
from src.infrastructure.data_fetcher.utils import rate_limit
from src.infrastructure.data_fetcher.claw_fetcher import ClawFetcher

class EastmoneyFinancialSearchInput(BaseModel):
    query: str = Field(..., description="搜索关键词，如 '宁德时代最新研报解读' 或 '半导体行业近期政策'")

def _sync(coro):
    """Internal helper to run async coro in sync tool."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

class EastmoneyFinancialSearchTool(BaseTool):
    name: str = "eastmoney_financial_search"
    description: str = (
        "基于东方财富妙想搜索能力进行金融场景信源检索。"
        "包含新闻、公告、研报、政策、交易规则等权威信息。"
        "若官方高级搜索限额，将降级到标准资讯接口。"
    )
    args_schema: Type[BaseModel] = EastmoneyFinancialSearchInput

    @rate_limit(calls_per_second=0.5, label="eastmoney")
    def _run(self, query: str) -> str:
        settings = get_settings()
        api_key = settings.eastmoney_api_key
        url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/news-search"
        
        headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        
        payload = {
            "query": query
        }
        
        # 1. 尝试官方新闻搜索接口
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == 0:
                        data = result.get("data", {})
                        if data.get("code") == "100":
                            inner_data = data.get("data", {})
                            if inner_data:
                                return json.dumps(inner_data, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # 2. 降级逻辑：尝试使用 ClawFetcher 的 fetch_news (通常针对个股)
        match = re.search(r'\d{6}', query)
        try:
            claw = ClawFetcher()
            # 如果提取到代码，精准搜索新闻
            search_key = match.group(0) if match else query
            news = _sync(claw.fetch_news(search_key, limit=5))
            if news and not any("暂无官方公开资讯" in n.get("title", "") for n in news):
                return json.dumps(news, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return "暂无相关权威信源或搜索授权限额。建议根据已有行情数据进行客观评估。"
