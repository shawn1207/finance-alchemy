"""CrewAI tool for Eastmoney Financial Data (Official API) with fallback logic."""

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
from src.infrastructure.data_fetcher.akshare_fetcher import AkShareFetcher

class EastmoneyFinancialDataInput(BaseModel):
    toolQuery: str = Field(..., description="自然语言查询内容，如 '600519的最新Roe和净利润率'")

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

class EastmoneyFinancialDataTool(BaseTool):
    name: str = "eastmoney_financial_data"
    description: str = (
        "基于东方财富权威数据库查询行情类数据（股票实时行情、资金流向、估值等）"
        "及财务类数据（基本信息、财务指标、高管信息等）。"
        "支持自然语言输入查询。若官方接口受限，将自动降级到备选数据源。"
    )
    args_schema: Type[BaseModel] = EastmoneyFinancialDataInput

    @rate_limit(calls_per_second=0.5, label="eastmoney")
    def _run(self, toolQuery: str) -> str:
        settings = get_settings()
        api_key = settings.eastmoney_api_key
        url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
        
        headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        
        payload = {
            "toolQuery": toolQuery
        }
        
        # 1. 尝试官方高级 Skill (NLP)
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
            pass # 继续尝试降级逻辑

        # 2. 尝试降级到传统的 Keyword Screening 接口 (ClawFetcher)
        # 尝试从输入文本中提取股票代码
        match = re.search(r'\d{6}', toolQuery)
        if match:
            stock_code = match.group(0)
            try:
                claw = ClawFetcher()
                # 优先尝试获取实时行情（因为 toolQuery 经常问行情）
                if any(x in toolQuery for x in ["现价", "行情", "涨幅", "价格", "实时"]):
                    data = _sync(claw.fetch_realtime_quote(stock_code))
                    if not data.get("error"):
                        return json.dumps(data, ensure_ascii=False, indent=2)
                
                # 否则尝试获取财务指标
                data = _sync(claw.fetch_financial_metrics(stock_code))
                if not data.get("error"):
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:
                pass

        # 3. 最终降级：AkShare 基础数据
        if match:
            stock_code = match.group(0)
            try:
                ak = AkShareFetcher()
                name = _sync(ak.get_stock_name(stock_code))
                # 仅返回最基础的名称确认
                return json.dumps({
                    "stock_name": name,
                    "stock_code": stock_code,
                    "warning": "官方高级 Skill 调用受限，已降级到基础数据源。部分详细财务指标可能缺失。"
                }, ensure_ascii=False)
            except Exception:
                pass

        return "抱歉，由于官方 API 限额或网络抖动，且无法在查询中识别具体股票代码，暂无法获取详细数据。"
