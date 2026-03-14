"""Financial metric value objects — pure data carriers with no external dependencies."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class FinancialMetrics(BaseModel):
    """Fundamental financial metrics for a listed company."""

    roe: Optional[Decimal] = None               # Return on Equity (净资产收益率)
    roa: Optional[Decimal] = None               # Return on Assets (总资产收益率)
    gross_margin: Optional[Decimal] = None       # 毛利率
    net_margin: Optional[Decimal] = None         # 净利率
    current_ratio: Optional[Decimal] = None      # 流动比率
    debt_to_equity: Optional[Decimal] = None     # 资产负债率
    pe_ratio: Optional[Decimal] = None           # 市盈率
    pb_ratio: Optional[Decimal] = None           # 市净率
    ps_ratio: Optional[Decimal] = None           # 市销率
    dividend_yield: Optional[Decimal] = None     # 股息率
    eps: Optional[Decimal] = None               # Earnings per Share (每股收益)
    revenue_growth: Optional[Decimal] = None     # 营收增速 (YoY %)
    profit_growth: Optional[Decimal] = None      # 净利润增速 (YoY %)

    model_config = {"frozen": True}


class MacroIndicators(BaseModel):
    """Macroeconomic indicators relevant to A-share market analysis."""

    gdp_growth: Optional[Decimal] = None    # GDP同比增速 (%)
    cpi: Optional[Decimal] = None           # 居民消费价格指数 (%)
    ppi: Optional[Decimal] = None           # 工业生产者出厂价格指数 (%)
    m2_growth: Optional[Decimal] = None     # M2货币供应量同比增速 (%)
    pmi: Optional[Decimal] = None           # 制造业采购经理人指数

    model_config = {"frozen": True}


class TechnicalIndicators(BaseModel):
    """Computed technical indicators for a stock at a point in time."""

    # Moving Averages
    ma5: Optional[Decimal] = None
    ma10: Optional[Decimal] = None
    ma20: Optional[Decimal] = None
    ma60: Optional[Decimal] = None

    # Momentum
    rsi14: Optional[Decimal] = None         # RSI (14-period)

    # MACD
    macd: Optional[Decimal] = None          # MACD line (DIF)
    macd_signal: Optional[Decimal] = None   # Signal line (DEA)
    macd_hist: Optional[Decimal] = None     # Histogram (MACD柱)

    # KDJ
    kdj_k: Optional[Decimal] = None
    kdj_d: Optional[Decimal] = None
    kdj_j: Optional[Decimal] = None

    # Bollinger Bands
    boll_upper: Optional[Decimal] = None
    boll_mid: Optional[Decimal] = None
    boll_lower: Optional[Decimal] = None

    # Volatility & Volume
    atr14: Optional[Decimal] = None         # Average True Range (14-period)
    volume_ratio: Optional[Decimal] = None  # 量比 (current volume / avg volume)

    model_config = {"frozen": True}
