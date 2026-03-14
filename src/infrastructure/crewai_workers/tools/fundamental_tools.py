"""CrewAI tools for fundamental analysis."""

import asyncio
from typing import Any, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ...data_fetcher.akshare_fetcher import AkShareFetcher
from ...data_fetcher.claw_fetcher import ClawFetcher
from ...data_fetcher.utils import rate_limit

_ak_fetcher = AkShareFetcher()
_claw_fetcher = ClawFetcher()


def _sync(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine synchronously (for CrewAI tool compatibility)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class _StockCodeInput(BaseModel):
    stock_code: str = Field(..., description="6位A股股票代码，例如 000001")


class FetchFinancialMetricsTool(BaseTool):
    name: str = "fetch_financial_metrics"
    description: str = (
        "获取A股上市公司的最新财务指标，包括ROE、ROA、毛利率、净利率、"
        "市盈率(PE)、市净率(PB)、营收增速、净利润增速等。输入6位股票代码。"
    )
    args_schema: Type[BaseModel] = _StockCodeInput

    def _run(self, stock_code: str) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            data = _sync(_claw_fetcher.fetch_financial_metrics(stock_code))
            
            if "error" in data:
                return f"股票：{name} ({stock_code})\n【!!! 数据缺失警告 !!!】\n{data['error']}\n提示：如果该工具未返回具体数字，你必须在报告中返回 NULL，绝对禁止根据经验或幻觉自拟数字。"
                
            # Key Mapping for normalization
            mapping = {
                "净资产收益率ROE(加权)(%)": "ROE (%)",
                "净利润/营业总收入(%)": "净利润率 (%)",
                "营业收入最新同比增长率": "营收增长率 (%)",
                "资产负债率(%)": "资产负债率 (%)",
                "流动比率(%)": "流动比率",
                "市盈率(动)(倍)": "PE (动)",
                "市盈率(TTM)(倍)": "PE (TTM)",
                "市净率(倍)": "PB",
                "现金分红比例(%)": "分红率 (%)",
                "总市值": "总市值 (亿)",
                "销售毛利率(%)": "销售毛利率 (%)",
                "销售毛利率": "销售毛利率 (%)",
                "归属母公司股东的净利润最新同比增长率(%)": "归母净利润增长率 (%)",
                "归属母公司股东的净利润最新同比增长率": "归母净利润增长率 (%)",
                "研发费用(含资本化)": "研发投入 (元/亿)"
            }
            
            lines = []
            for k, v in data.items():
                if k.startswith("_") or k in ["序号", "代码", "名称", "市场代码简称"]:
                    continue
                
                # Normalize title
                display_title = mapping.get(k, k)
                
                # Clean value (strip period info like |2025三季报)
                if isinstance(v, str) and "|" in v:
                    clean_val = v.split("|")[0]
                    lines.append(f"  - {display_title}: {clean_val} (原始报表周期: {v.split('|')[1]})")
                else:
                    lines.append(f"  - {display_title}: {v}")
                
            source = data.get("_raw_source", "官方高级数据源")
            return f"股票：{name} ({stock_code})\n【{source}】核心财务指标：\n" + "\n".join(lines)
        except Exception as e:
            return f"获取官方财务数据失败 ({stock_code}): {e}。请优先返回 NULL。"


class _MacroInput(BaseModel):
    indicator: str = Field(
        default="all",
        description="宏观指标类型: gdp / cpi / ppi / pmi / m2 / all",
    )


class FetchMacroIndicatorsTool(BaseTool):
    name: str = "fetch_macro_indicators"
    description: str = (
        "获取中国宏观经济指标，包括GDP增速、CPI、PPI、M2货币供应量增速、PMI制造业指数等。"
        "用于评估宏观经济环境对A股市场的整体影响。"
    )
    args_schema: Type[BaseModel] = _MacroInput

    @rate_limit(calls_per_second=0.5, label="akshare")
    def _run(self, indicator: str = "all") -> str:
        try:
            import akshare as ak  # type: ignore[import-untyped]

            results: list[str] = []

            if indicator in ("gdp", "all"):
                try:
                    df = ak.macro_china_gdp()
                    if df is not None and not df.empty:
                        latest = df.iloc[-1].to_dict()
                        results.append(f"GDP: {latest}")
                except Exception:
                    results.append("GDP数据暂不可用")

            if indicator in ("cpi", "all"):
                try:
                    df = ak.macro_china_cpi_yearly()
                    if df is not None and not df.empty:
                        latest = df.iloc[-1].to_dict()
                        results.append(f"CPI(年率): {latest}")
                except Exception:
                    results.append("CPI数据暂不可用")

            if indicator in ("pmi", "all"):
                try:
                    df = ak.macro_china_pmi_yearly()
                    if df is not None and not df.empty:
                        latest = df.iloc[-1].to_dict()
                        results.append(f"PMI: {latest}")
                except Exception:
                    results.append("PMI数据暂不可用")

            return "\n".join(results) if results else "宏观数据暂无"
        except Exception as e:
            return f"获取宏观数据失败: {e}"


class FetchStockNewsTool(BaseTool):
    name: str = "fetch_stock_news"
    description: str = (
        "获取指定A股股票的最新新闻资讯，用于分析市场情绪和重要事件。输入6位股票代码。"
    )
    args_schema: Type[BaseModel] = _StockCodeInput

    def _run(self, stock_code: str) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            news = _sync(_claw_fetcher.fetch_news(stock_code, limit=10))
            if not news:
                return f"暂无关于 {name} ({stock_code}) 的官方资讯。"
            
            lines = []
            for item in news:
                title = item.get("title", item.get("新闻标题", "无标题"))
                publish_time = item.get("publishTime", item.get("发布时间", item.get("date", "未知时间")))
                source = item.get("source", "未知来源")
                lines.append(f"- [{publish_time}] {title} (来源: {source})")
            
            return f"股票：{name} ({stock_code})\n【官方资讯搜索】最新动态：\n" + "\n".join(lines)
        except Exception as e:
            return f"获取官方资讯失败 ({stock_code}): {e}"
