"""Data fetcher exceptions."""


class DataFetchError(Exception):
    """Base exception for all data fetching errors."""


class DataNotFoundError(DataFetchError):
    """Raised when requested data does not exist."""


class RateLimitError(DataFetchError):
    """Raised when the data source rate limit is exceeded."""


class NetworkError(DataFetchError):
    """Raised when a network-level failure occurs."""
