"""Pure domain service for technical indicator calculations.

No external framework dependencies — only Python stdlib and numpy/pandas.
All methods are static and return None when data is insufficient.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import numpy as np


class TechnicalCalculator:
    """Stateless technical analysis calculator.

    All methods operate on lists of Decimal values and return Decimal results.
    Returns None when there is insufficient data for the requested period.
    """

    @staticmethod
    def calculate_ma(prices: list[Decimal], period: int) -> Optional[Decimal]:
        """Calculate Simple Moving Average (SMA) over the last `period` bars.

        Args:
            prices: Chronologically ordered close prices.
            period: Look-back window size.

        Returns:
            Decimal MA value, or None if len(prices) < period.
        """
        if len(prices) < period:
            return None
        window = prices[-period:]
        avg = sum(window) / period
        return avg.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_rsi(prices: list[Decimal], period: int = 14) -> Optional[Decimal]:
        """Calculate Relative Strength Index (RSI).

        Uses Wilder's smoothing method (EMA-based).

        Args:
            prices: Chronologically ordered close prices.
            period: RSI period (default 14).

        Returns:
            RSI value in [0, 100], or None if insufficient data.
        """
        if len(prices) < period + 1:
            return None

        floats = [float(p) for p in prices]
        deltas = np.diff(floats)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return Decimal("100")

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return Decimal(str(round(rsi, 4)))

    @staticmethod
    def calculate_macd(
        prices: list[Decimal],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Optional[tuple[Decimal, Decimal, Decimal]]:
        """Calculate MACD indicator (DIF, DEA, Histogram).

        Args:
            prices: Chronologically ordered close prices.
            fast: Fast EMA period (default 12).
            slow: Slow EMA period (default 26).
            signal: Signal EMA period (default 9).

        Returns:
            Tuple (macd_line, signal_line, histogram) or None if insufficient data.
        """
        required = slow + signal - 1
        if len(prices) < required:
            return None

        floats = np.array([float(p) for p in prices])

        def ema(data: np.ndarray, n: int) -> np.ndarray:
            k = 2.0 / (n + 1)
            result = np.empty(len(data))
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = data[i] * k + result[i - 1] * (1 - k)
            return result

        ema_fast = ema(floats, fast)
        ema_slow = ema(floats, slow)
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal)
        histogram = macd_line - signal_line

        return (
            Decimal(str(round(macd_line[-1], 4))),
            Decimal(str(round(signal_line[-1], 4))),
            Decimal(str(round(histogram[-1], 4))),
        )

    @staticmethod
    def calculate_kdj(
        highs: list[Decimal],
        lows: list[Decimal],
        closes: list[Decimal],
        period: int = 9,
    ) -> Optional[tuple[Decimal, Decimal, Decimal]]:
        """Calculate KDJ stochastic oscillator.

        Args:
            highs: Chronologically ordered high prices.
            lows: Chronologically ordered low prices.
            closes: Chronologically ordered close prices.
            period: RSV look-back period (default 9).

        Returns:
            Tuple (K, D, J) values, or None if insufficient data.
        """
        if len(closes) < period:
            return None

        h = np.array([float(x) for x in highs[-period:]])
        l = np.array([float(x) for x in lows[-period:]])
        c = float(closes[-1])

        highest_h = np.max(h)
        lowest_l = np.min(l)

        if highest_h == lowest_l:
            rsv = 50.0
        else:
            rsv = (c - lowest_l) / (highest_h - lowest_l) * 100

        k = (2.0 / 3.0) * 50 + (1.0 / 3.0) * rsv  # simplified single-bar K
        d = (2.0 / 3.0) * 50 + (1.0 / 3.0) * k
        j = 3.0 * k - 2.0 * d

        return (
            Decimal(str(round(k, 4))),
            Decimal(str(round(d, 4))),
            Decimal(str(round(j, 4))),
        )

    @staticmethod
    def detect_volume_anomaly(
        volumes: list[Decimal],
        threshold: float = 2.0,
    ) -> bool:
        """Detect whether the latest volume bar is anomalously large.

        An anomaly is flagged when the latest volume exceeds `threshold`
        times the mean volume of the preceding bars.

        Args:
            volumes: Chronologically ordered volume data (latest last).
            threshold: Multiplier above mean to flag as anomaly (default 2.0).

        Returns:
            True if the latest volume is anomalously high, False otherwise.
        """
        if len(volumes) < 2:
            return False

        historical = [float(v) for v in volumes[:-1]]
        current = float(volumes[-1])
        mean_vol = float(np.mean(historical))

        if mean_vol == 0:
            return False

        return current >= threshold * mean_vol

    @staticmethod
    def calculate_bollinger_bands(
        prices: list[Decimal],
        period: int = 20,
        std_dev: int = 2,
    ) -> Optional[tuple[Decimal, Decimal, Decimal]]:
        """Calculate Bollinger Bands (upper, mid, lower).

        Args:
            prices: Chronologically ordered close prices.
            period: MA period (default 20).
            std_dev: Number of standard deviations (default 2).

        Returns:
            Tuple (upper, mid, lower) or None if insufficient data.
        """
        if len(prices) < period:
            return None

        window = [float(p) for p in prices[-period:]]
        mid = float(np.mean(window))
        std = float(np.std(window, ddof=0))

        upper = mid + std_dev * std
        lower = mid - std_dev * std

        return (
            Decimal(str(round(upper, 4))),
            Decimal(str(round(mid, 4))),
            Decimal(str(round(lower, 4))),
        )
