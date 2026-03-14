"""A-share Stock domain entity."""

import re
from enum import StrEnum

from pydantic import BaseModel, field_validator


class Market(StrEnum):
    """A-share trading market."""

    SH = "SH"  # Shanghai Stock Exchange
    SZ = "SZ"  # Shenzhen Stock Exchange
    BJ = "BJ"  # Beijing Stock Exchange


_ASHARE_PATTERN = re.compile(r"^\d{6}$")

_MARKET_PREFIX_MAP: dict[str, Market] = {
    "60": Market.SH,
    "68": Market.SH,  # STAR Market (科创板)
    "00": Market.SZ,
    "30": Market.SZ,  # ChiNext (创业板)
    "83": Market.BJ,
    "87": Market.BJ,
    "43": Market.BJ,
}


def infer_market(code: str) -> Market:
    """Infer market from stock code prefix."""
    prefix = code[:2]
    market = _MARKET_PREFIX_MAP.get(prefix)
    if market is None:
        raise ValueError(f"Cannot infer market from code prefix '{prefix}' for code '{code}'")
    return market


class StockCode(str):
    """Value object representing a validated A-share stock code."""

    @classmethod
    def __get_validators__(cls):  # type: ignore[override]
        yield cls.validate

    @classmethod
    def validate(cls, v: object) -> "StockCode":
        if not isinstance(v, str):
            raise TypeError("StockCode must be a string")
        if not _ASHARE_PATTERN.match(v):
            raise ValueError(f"Invalid A-share code '{v}': must be exactly 6 digits")
        return cls(v)


class Stock(BaseModel):
    """Core A-share stock entity.

    Represents a listed company on the Chinese A-share market.
    This entity is pure domain — no framework dependencies.
    """

    code: str
    name: str
    market: Market
    sector: str = ""
    industry: str = ""

    model_config = {"frozen": True}

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not _ASHARE_PATTERN.match(v):
            raise ValueError(f"Invalid A-share code '{v}': must be exactly 6 digits")
        return v

    @property
    def full_code(self) -> str:
        """Return market-qualified code, e.g. '000001.SZ'."""
        return f"{self.code}.{self.market}"

    def __str__(self) -> str:
        return f"{self.name}({self.full_code})"
