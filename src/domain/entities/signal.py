"""Trading Signal and Decision domain entities."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SignalType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(StrEnum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class SignalSource(StrEnum):
    FUNDAMENTAL = "FUNDAMENTAL"
    TECHNICAL = "TECHNICAL"
    COMBINED = "COMBINED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Signal(BaseModel):
    """Trading signal produced by an analysis agent."""

    stock_code: str
    signal_type: SignalType
    strength: SignalStrength
    source: SignalSource
    reason: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score [0, 1]")
    timestamp: datetime

    model_config = {"frozen": True}


class TradeDecision(BaseModel):
    """Actionable trade decision with risk management parameters."""

    signal: Signal
    position_size_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Recommended position size as % of portfolio"
    )
    stop_loss_pct: float = Field(..., gt=0.0, description="Stop-loss distance as % from entry")
    take_profit_pct: float = Field(..., gt=0.0, description="Take-profit target as % from entry")
    risk_level: RiskLevel
    rationale: str

    model_config = {"frozen": True}

    @property
    def risk_reward_ratio(self) -> float:
        """Reward-to-risk ratio (take_profit / stop_loss)."""
        return self.take_profit_pct / self.stop_loss_pct
