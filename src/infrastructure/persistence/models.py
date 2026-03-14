from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class AnalysisReportModel(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    
    # Strategy Results
    decision = Column(String(20), nullable=False)
    confidence = Column(Float)
    position_size_pct = Column(Float)
    stop_loss_pct = Column(Float)
    take_profit_pct = Column(Float)
    risk_level = Column(String(20))
    rationale = Column(Text)
    
    # Summaries (JSON or Text)
    fundamental_summary = Column(Text)
    technical_summary = Column(Text)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.now)
    duration_seconds = Column(Float)

    # Full Result Dump (for future compatibility or re-parsing)
    raw_json = Column(Text)

    def __repr__(self):
        return f"<AnalysisReport(stock_code='{self.stock_code}', decision='{self.decision}')>"
