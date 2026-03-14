from typing import Optional, List
from sqlalchemy.orm import Session
from src.domain.repositories.analysis_repository import AnalysisRepository
from src.application.dto.analysis_dto import StockAnalysisResult, StrategyReport, FundamentalReport, TechnicalReport
from .models import AnalysisReportModel
from .database import get_db_session, init_db

class SQLiteAnalysisRepository(AnalysisRepository):
    """SQLite implementation of the analysis repository using SQLAlchemy."""

    def __init__(self):
        init_db()  # Ensure tables exist

    def save(self, result: StockAnalysisResult) -> str:
        with get_db_session() as session:
            model = AnalysisReportModel(
                stock_code=result.request.stock_code,
                decision=result.strategy.decision,
                confidence=result.strategy.confidence,
                position_size_pct=result.strategy.position_size_pct,
                stop_loss_pct=result.strategy.stop_loss_pct,
                take_profit_pct=result.strategy.take_profit_pct,
                risk_level=result.strategy.risk_level,
                rationale=result.strategy.rationale,
                fundamental_summary=result.strategy.fundamental_summary,
                technical_summary=result.strategy.technical_summary,
                generated_at=result.strategy.generated_at,
                duration_seconds=result.duration_seconds,
                raw_json=result.model_dump_json() if hasattr(result, 'model_dump_json') else str(result)
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return str(model.id)

    def get_by_id(self, report_id: str) -> Optional[StockAnalysisResult]:
        # Basic implementation, can be expanded to reconstruct the DTO
        with get_db_session() as session:
            model = session.query(AnalysisReportModel).filter(AnalysisReportModel.id == int(report_id)).first()
            if not model:
                return None
            # Simplest way is to reconstruct from raw_json if it exists
            if model.raw_json:
                import json
                try:
                    data = json.loads(model.raw_json)
                    return StockAnalysisResult(**data)
                except:
                    pass
            return None

    def list_by_stock(self, stock_code: str, limit: int = 10) -> List[StockAnalysisResult]:
        with get_db_session() as session:
            models = session.query(AnalysisReportModel)\
                .filter(AnalysisReportModel.stock_code == stock_code)\
                .order_by(AnalysisReportModel.generated_at.desc())\
                .limit(limit).all()
            
            results = []
            for m in models:
                if m.raw_json:
                    try:
                        import json
                        results.append(StockAnalysisResult(**json.loads(m.raw_json)))
                    except:
                        continue
            return results
