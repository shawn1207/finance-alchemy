"""Data Transfer Objects for the stock analysis use case."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class StockAnalysisRequest(BaseModel):
    """Input DTO for a stock analysis request."""

    stock_code: str = Field(..., description="A股股票代码, e.g. 000001")
    include_fundamental: bool = True
    include_technical: bool = True
    kline_limit: int = Field(200, ge=10, le=1000, description="K线条数")
    refine_roles: bool = Field(False, description="是否使用大模型进一步修饰智能体角色描述")


class FundamentalReport(BaseModel):
    """Output from the fundamental analysis agent."""

    stock_code: str
    analysis_text: str
    roe: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    revenue_growth: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    net_profit_growth: Optional[Decimal] = None
    sentiment: str = "NEUTRAL"  # BULLISH / BEARISH / NEUTRAL
    generated_at: datetime

    @field_validator("roe", "pe_ratio", "revenue_growth", "gross_margin", "net_profit_growth", mode="before")
    @classmethod
    def coerce_decimal_or_none(cls, v):
        """Coerce common 'missing' string representations to None."""
        if isinstance(v, str):
            clean_v = v.strip().upper()
            if clean_v in ("N/A", "NULL", "-", "NONE", ""):
                return None
        return v


class TechnicalReport(BaseModel):
    """Output from the technical analysis agent."""

    stock_code: str
    analysis_text: str
    trend: str = "SIDEWAYS"  # UPTREND / DOWNTREND / SIDEWAYS
    rsi: Optional[Decimal] = None
    macd_signal: str = "NEUTRAL"  # BULLISH / BEARISH / NEUTRAL
    volume_anomaly: bool = False
    generated_at: datetime

    @field_validator("rsi", mode="before")
    @classmethod
    def coerce_technical_decimal(cls, v):
        """Coerce common 'missing' string representations to None."""
        if isinstance(v, str):
            clean_v = v.strip().upper()
            if clean_v in ("N/A", "NULL", "-", "NONE", ""):
                return None
        return v


class StrategyReport(BaseModel):
    """Final trade decision from the strategy agent."""

    stock_code: str
    decision: str  # BUY / SELL / HOLD
    confidence: float = Field(..., ge=0.0, le=1.0)
    position_size_pct: float = Field(..., ge=0.0, le=100.0)
    stop_loss_pct: float
    take_profit_pct: float
    risk_level: str  # LOW / MEDIUM / HIGH
    rationale: str
    fundamental_summary: str
    technical_summary: str
    generated_at: datetime


class AuditReport(BaseModel):
    """Output from the data audit/risk control agent."""

    stock_code: str
    is_verified: bool = Field(..., description="Whether the data and logic passed the audit")
    risk_warnings: list[str] = Field(default_factory=list, description="List of detected hallucinations or contradictions")
    audit_notes: str = Field(..., description="Detailed explanation of the audit findings")
    generated_at: datetime


class StockAnalysisResult(BaseModel):
    """Composite result returned to the interface layer."""

    request: StockAnalysisRequest
    fundamental: Optional[FundamentalReport] = None
    technical: Optional[TechnicalReport] = None
    strategy: StrategyReport
    audit: Optional[AuditReport] = None
    backtest: Optional[dict] = None
    raw_data_appendix: Optional[str] = None
    audit_log: list[str] = Field(default_factory=list, description="History of audit rejections and retries")
    duration_seconds: float
