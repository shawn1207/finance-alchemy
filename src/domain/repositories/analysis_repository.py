from abc import ABC, abstractmethod
from typing import Optional, List
from src.application.dto.analysis_dto import StockAnalysisResult

class AnalysisRepository(ABC):
    """Abstract base class for stock analysis persistence."""

    @abstractmethod
    def save(self, result: StockAnalysisResult) -> str:
        """Save analysis result and return its ID."""
        pass

    @abstractmethod
    def get_by_id(self, report_id: str) -> Optional[StockAnalysisResult]:
        """Retrieve analysis result by ID."""
        pass

    @abstractmethod
    def list_by_stock(self, stock_code: str, limit: int = 10) -> List[StockAnalysisResult]:
        """List recent analysis results for a specific stock."""
        pass
