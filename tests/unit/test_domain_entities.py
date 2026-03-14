"""Unit tests for domain layer entities."""

import pytest
from decimal import Decimal
from datetime import datetime

from src.domain.entities.stock import Stock, Market
from src.domain.entities.kline import KLine, KLineInterval, KLineSeries
from src.domain.entities.signal import (
    Signal, SignalType, SignalStrength, SignalSource,
    TradeDecision, RiskLevel,
)


class TestStockEntity:
    def test_valid_sz_stock(self):
        stock = Stock(code="000001", name="平安银行", market=Market.SZ, sector="金融", industry="银行")
        assert stock.code == "000001"
        assert stock.market == Market.SZ
        assert stock.full_code == "000001.SZ"

    def test_valid_sh_stock(self):
        stock = Stock(code="600036", name="招商银行", market=Market.SH)
        assert stock.market == Market.SH
        assert stock.full_code == "600036.SH"

    def test_invalid_stock_code_letters(self):
        with pytest.raises(Exception):
            Stock(code="ABCDEF", name="Test", market=Market.SZ)

    def test_invalid_stock_code_too_short(self):
        with pytest.raises(Exception):
            Stock(code="0001", name="Test", market=Market.SZ)

    def test_stock_str(self):
        stock = Stock(code="000001", name="平安银行", market=Market.SZ)
        assert "000001" in str(stock)
        assert "平安银行" in str(stock)


class TestKLineEntity:
    def _make_kline(self, ts: datetime, close: float = 10.0) -> KLine:
        return KLine(
            stock_code="000001",
            interval=KLineInterval.DAILY,
            open=Decimal("10.0"),
            high=Decimal("11.0"),
            low=Decimal("9.0"),
            close=Decimal(str(close)),
            volume=Decimal("1000000"),
            amount=Decimal("10000000"),
            timestamp=ts,
        )

    def test_kline_series_latest(self):
        t1 = datetime(2024, 1, 1)
        t2 = datetime(2024, 1, 2)
        series = KLineSeries(
            stock_code="000001",
            interval=KLineInterval.DAILY,
            bars=[self._make_kline(t1), self._make_kline(t2, close=12.0)],
        )
        latest = series.latest(1)
        assert len(latest) == 1
        assert latest[0].timestamp == t2

    def test_kline_series_date_range(self):
        bars = [self._make_kline(datetime(2024, 1, i)) for i in range(1, 6)]
        series = KLineSeries(stock_code="000001", interval=KLineInterval.DAILY, bars=bars)
        filtered = series.date_range(datetime(2024, 1, 2), datetime(2024, 1, 4))
        assert len(filtered.bars) == 3

    def test_kline_negative_price_rejected(self):
        with pytest.raises(Exception):
            KLine(
                stock_code="000001",
                interval=KLineInterval.DAILY,
                open=Decimal("-1"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
                volume=Decimal("1000"),
                amount=Decimal("10000"),
                timestamp=datetime.now(),
            )

    def test_kline_high_lt_low_rejected(self):
        with pytest.raises(Exception):
            KLine(
                stock_code="000001",
                interval=KLineInterval.DAILY,
                open=Decimal("10"),
                high=Decimal("8"),   # high < low — invalid
                low=Decimal("9"),
                close=Decimal("10"),
                volume=Decimal("1000"),
                amount=Decimal("10000"),
                timestamp=datetime.now(),
            )

    def test_close_prices(self):
        bars = [self._make_kline(datetime(2024, 1, i), close=float(i * 10)) for i in range(1, 4)]
        series = KLineSeries(stock_code="000001", interval=KLineInterval.DAILY, bars=bars)
        prices = series.close_prices()
        assert prices == [Decimal("10"), Decimal("20"), Decimal("30")]


class TestSignalEntity:
    def test_signal_confidence_range_valid(self):
        sig = Signal(
            stock_code="000001",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            source=SignalSource.COMBINED,
            reason="Test",
            confidence=0.85,
            timestamp=datetime.now(),
        )
        assert sig.confidence == 0.85

    def test_signal_confidence_out_of_range(self):
        with pytest.raises(Exception):
            Signal(
                stock_code="000001",
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                source=SignalSource.TECHNICAL,
                reason="Test",
                confidence=1.5,   # > 1.0 — invalid
                timestamp=datetime.now(),
            )

    def test_trade_decision_risk_reward(self):
        sig = Signal(
            stock_code="000001",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            source=SignalSource.COMBINED,
            reason="Test",
            confidence=0.7,
            timestamp=datetime.now(),
        )
        decision = TradeDecision(
            signal=sig,
            position_size_pct=20.0,
            stop_loss_pct=5.0,
            take_profit_pct=15.0,
            risk_level=RiskLevel.MEDIUM,
            rationale="Test rationale",
        )
        assert decision.risk_reward_ratio == pytest.approx(3.0)
