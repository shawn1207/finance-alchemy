"""CrewAI tools for technical analysis."""

import asyncio
from decimal import Decimal
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ...data_fetcher.akshare_fetcher import AkShareFetcher
from ...data_fetcher.claw_fetcher import ClawFetcher
from ....domain.services.technical_calculator import TechnicalCalculator

_ak_fetcher = AkShareFetcher()
_claw_fetcher = ClawFetcher()


def _sync(coro):  # type: ignore[no-untyped-def]
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class _KLineInput(BaseModel):
    stock_code: str = Field(..., description="6位A股股票代码")
    interval: str = Field(default="daily", description="K线周期: daily/weekly/monthly/60m/30m/15m/5m/1m")
    limit: int = Field(default=200, ge=10, le=1000, description="获取条数")


class FetchKLineTool(BaseTool):
    name: str = "fetch_kline_data"
    description: str = "获取A股股票的K线数据(OHLCV)，支持日线、周线、月线及分钟线。"
    args_schema: Type[BaseModel] = _KLineInput

    def _run(self, stock_code: str, interval: str = "daily", limit: int = 200) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            df = _sync(_claw_fetcher.fetch_kline(stock_code, interval, limit))
            if df.empty:
                return f"无K线数据: {name} ({stock_code})"
            latest = df.iloc[-1]
            return (
                f"股票：{name} ({stock_code})\nK线数据（共{len(df)}条，最新）：\n"
                f"  时间: {latest.get('timestamp', 'N/A')}\n"
                f"  开: {latest.get('open', 'N/A')}\n"
                f"  高: {latest.get('high', 'N/A')}\n"
                f"  低: {latest.get('low', 'N/A')}\n"
                f"  收: {latest.get('close', 'N/A')}\n"
                f"  量: {latest.get('volume', 'N/A')}"
            )
        except Exception as e:
            return f"获取K线失败 ({stock_code}): {e}"


class _StockCodeInput(BaseModel):
    stock_code: str = Field(..., description="6位A股股票代码")


class CalculateTechnicalIndicatorsTool(BaseTool):
    name: str = "calculate_technical_indicators"
    description: str = (
        "计算A股股票的全套技术指标：MA(5/10/20/60)、RSI(14)、MACD、KDJ、布林带。"
        "输入股票代码，自动获取K线数据并计算。"
    )
    args_schema: Type[BaseModel] = _StockCodeInput

    def _run(self, stock_code: str) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            df = _sync(_ak_fetcher.fetch_kline(stock_code, "daily", 200))
            if df.empty:
                return f"无法计算指标: {name} ({stock_code}) 无K线数据"

            closes = [Decimal(str(p)) for p in df["close"].tolist()]
            highs = [Decimal(str(p)) for p in df["high"].tolist()]
            lows = [Decimal(str(p)) for p in df["low"].tolist()]

            results = [f"**股票：{name} ({stock_code}) 技术指标分析**"]

            for period in (5, 10, 20, 60):
                ma = TechnicalCalculator.calculate_ma(closes, period)
                results.append(f"  MA{period}: {ma or 'N/A'}")

            rsi = TechnicalCalculator.calculate_rsi(closes)
            results.append(f"  RSI(14): {rsi or 'N/A'}")
            if rsi:
                if float(rsi) > 70:
                    results.append("    → RSI超买区域")
                elif float(rsi) < 30:
                    results.append("    → RSI超卖区域")

            macd = TechnicalCalculator.calculate_macd(closes)
            if macd:
                results.append(f"  MACD(DIF): {macd[0]}, DEA: {macd[1]}, 柱: {macd[2]}")
                if float(macd[2]) > 0:
                    results.append("    → MACD金叉/多头")
                else:
                    results.append("    → MACD死叉/空头")

            kdj = TechnicalCalculator.calculate_kdj(highs, lows, closes)
            if kdj:
                results.append(f"  KDJ: K={kdj[0]}, D={kdj[1]}, J={kdj[2]}")

            bb = TechnicalCalculator.calculate_bollinger_bands(closes)
            if bb:
                results.append(f"  布林带: 上={bb[0]}, 中={bb[1]}, 下={bb[2]}")

            return "\n".join(results)
        except Exception as e:
            return f"技术指标计算失败 ({stock_code}): {e}"


class DetectVolumeAnomalyTool(BaseTool):
    name: str = "detect_volume_anomaly"
    description: str = "检测A股股票成交量是否出现异常放量，帮助识别主力资金动向。"
    args_schema: Type[BaseModel] = _StockCodeInput

    def _run(self, stock_code: str) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            df = _sync(_ak_fetcher.fetch_kline(stock_code, "daily", 60))
            if df.empty or len(df) < 2:
                return f"数据不足，无法检测量能异常: {name} ({stock_code})"

            volumes = [Decimal(str(v)) for v in df["volume"].tolist()]
            is_anomaly = TechnicalCalculator.detect_volume_anomaly(volumes, threshold=2.0)
            latest_vol = volumes[-1]
            avg_vol = sum(volumes[:-1]) / (len(volumes) - 1)

            status = "⚠️  异常放量" if is_anomaly else "正常"
            return (
                f"股票：{name} ({stock_code}) 量能分析：\n"
                f"  当日成交量: {latest_vol:,.0f}\n"
                f"  近期平均量: {avg_vol:,.0f}\n"
                f"  量量比: {float(latest_vol / avg_vol):.2f}x\n"
                f"  状态: {status}"
            )
        except Exception as e:
            return f"量能检测失败 ({stock_code}): {e}"

class FetchOfficialTechnicalAnalysisTool(BaseTool):
    name: str = "fetch_official_technical_analysis"
    description: str = (
        "获取东方财富官方提供的深度技术面分析，包括核心指标趋势、形态识别及强弱评估。"
        "包含基于官方高保真算法计算的 MA, RSI, MACD, KDJ 等指标结论。"
    )
    args_schema: Type[BaseModel] = _StockCodeInput

    def _run(self, stock_code: str) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            data = _sync(_claw_fetcher.fetch_technical_analysis(stock_code))
            
            summary = data.get("summary", "无摘要报告")
            indicators = data.get("indicators", {})
            
            results = [f"**股票：{name} ({stock_code}) 官方深度技术分析**"]
            results.append(f"【分析结论】: {summary}")
            results.append("\n【核心指标实时数据】:")
            for k, v in indicators.items():
                if k in ["序号", "代码", "名称", "市场代码简称"] or k.startswith("CHOICE"):
                    continue
                results.append(f"  - {k}: {v}")
                
            return "\n".join(results)
        except Exception as e:
            return f"获取官方技术分析失败 ({stock_code}): {e}"


class FetchRealtimeQuoteTool(BaseTool):
    name: str = "fetch_realtime_quote"
    description: str = "获取A股股票实时行情快照，包括当前价格、涨跌幅、成交量等。"
    args_schema: Type[BaseModel] = _StockCodeInput

    def _run(self, stock_code: str) -> str:
        try:
            name = _sync(_ak_fetcher.get_stock_name(stock_code))
            data = _sync(_claw_fetcher.fetch_realtime_quote(stock_code))
            
            price = data.get("price", "N/A")
            change = data.get("changePercent", data.get("pct_change", "N/A"))
            volume = data.get("volume", "N/A")
            
            return (
                f"股票：{name} ({stock_code}) 实时行情快照：\n"
                f"  最新价: {price}\n"
                f"  涨跌幅: {change}%\n"
                f"  成交量: {volume} 手"
            )
        except Exception as e:
            return f"获取实时行情失败 ({stock_code}): {e}"
