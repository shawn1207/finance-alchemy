"""Unit tests for TechnicalCalculator domain service."""

import pytest
from decimal import Decimal

from src.domain.services.technical_calculator import TechnicalCalculator


def _d(values: list[float]) -> list[Decimal]:
    return [Decimal(str(v)) for v in values]


class TestMovingAverage:
    def test_simple_5_period_ma(self):
        prices = _d([10, 11, 12, 13, 14, 15])
        result = TechnicalCalculator.calculate_ma(prices, 5)
        assert result is not None
        assert result == Decimal("13.0000")  # mean of [11,12,13,14,15]

    def test_ma_with_exact_period_length(self):
        prices = _d([10, 20, 30])
        result = TechnicalCalculator.calculate_ma(prices, 3)
        assert result == Decimal("20.0000")

    def test_ma_returns_none_for_insufficient_data(self):
        prices = _d([10, 11])
        result = TechnicalCalculator.calculate_ma(prices, 5)
        assert result is None

    def test_ma_period_one(self):
        prices = _d([42.5])
        result = TechnicalCalculator.calculate_ma(prices, 1)
        assert result is not None
        assert float(result) == pytest.approx(42.5, rel=1e-3)


class TestRSI:
    def test_rsi_returns_none_for_insufficient_data(self):
        prices = _d(list(range(10)))  # < 15 needed for period=14
        result = TechnicalCalculator.calculate_rsi(prices, period=14)
        assert result is None

    def test_rsi_in_valid_range(self):
        import random
        random.seed(42)
        prices = _d([100 + random.uniform(-5, 5) for _ in range(50)])
        result = TechnicalCalculator.calculate_rsi(prices, period=14)
        assert result is not None
        assert Decimal("0") <= result <= Decimal("100")

    def test_rsi_all_gains_returns_100(self):
        # Strictly increasing prices → RSI should approach 100
        prices = _d([float(i) for i in range(1, 30)])
        result = TechnicalCalculator.calculate_rsi(prices, period=14)
        assert result is not None
        assert float(result) > 90


class TestMACD:
    def test_macd_returns_none_for_insufficient_data(self):
        prices = _d([10.0] * 10)  # need at least 26+9-1=34
        result = TechnicalCalculator.calculate_macd(prices)
        assert result is None

    def test_macd_returns_three_values(self):
        prices = _d([float(i) + 100 for i in range(60)])
        result = TechnicalCalculator.calculate_macd(prices)
        assert result is not None
        assert len(result) == 3

    def test_macd_types(self):
        prices = _d([float(i) + 100 for i in range(60)])
        result = TechnicalCalculator.calculate_macd(prices)
        assert result is not None
        for val in result:
            assert isinstance(val, Decimal)


class TestBollingerBands:
    def test_bollinger_returns_none_for_insufficient_data(self):
        prices = _d([10.0] * 5)
        result = TechnicalCalculator.calculate_bollinger_bands(prices, period=20)
        assert result is None

    def test_upper_greater_than_lower(self):
        prices = _d([10 + i * 0.1 for i in range(30)])
        result = TechnicalCalculator.calculate_bollinger_bands(prices)
        assert result is not None
        upper, mid, lower = result
        assert upper >= lower

    def test_mid_between_upper_and_lower(self):
        prices = _d([10 + i * 0.1 for i in range(30)])
        result = TechnicalCalculator.calculate_bollinger_bands(prices)
        assert result is not None
        upper, mid, lower = result
        assert lower <= mid <= upper


class TestVolumeAnomaly:
    def test_no_anomaly_for_normal_volume(self):
        volumes = _d([1_000_000] * 20 + [1_100_000])  # only 1.1x avg
        result = TechnicalCalculator.detect_volume_anomaly(volumes, threshold=2.0)
        assert result is False

    def test_anomaly_detected_for_high_volume(self):
        volumes = _d([1_000_000] * 20 + [5_000_000])  # 5x avg
        result = TechnicalCalculator.detect_volume_anomaly(volumes, threshold=2.0)
        assert result is True

    def test_insufficient_data_returns_false(self):
        result = TechnicalCalculator.detect_volume_anomaly(_d([1_000_000]))
        assert result is False
