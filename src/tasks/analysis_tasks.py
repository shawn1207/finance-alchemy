"""Celery tasks for stock analysis."""

from celery.utils.log import get_task_logger
from langchain_openai import ChatOpenAI

from ..application.dto.analysis_dto import StockAnalysisRequest
from src.application.use_cases.analyze_stock import AnalyzeStockUseCase
from ..config import get_settings
from .celery_app import celery_app
import os
import traceback
from datetime import datetime

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def run_stock_analysis_task(self, request_data: dict):
    """Celery task to run the stock analysis use case."""
    try:
        logger.info(f"Starting analysis for task {self.request.id}")
        
        # Recreate request object from dictionary
        request = StockAnalysisRequest(**request_data)
        
        # Initialize LLM and UseCase inside the task
        from crewai import LLM
        settings = get_settings()
        llm = LLM(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )
        from ..infrastructure.persistence.sqlite_repository import SQLiteAnalysisRepository
        repository = SQLiteAnalysisRepository()
        use_case = AnalyzeStockUseCase(llm=llm, repository=repository)
        
        # Execute the analysis
        result = use_case.execute(request)
        
        logger.info(f"Analysis for task {self.request.id} completed successfully.")
        
        # The use case returns an object with the result path, so we return that path.
        return result.model_dump()

    except Exception as e:
        logger.error(f"Task {self.request.id} failed: {e}", exc_info=True)
        
        # Log to local cache for user to see
        try:
            os.makedirs(".cache/logs", exist_ok=True)
            log_path = ".cache/logs/error.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_details = traceback.format_exc()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] CELERY ERROR (Task {self.request.id}): {str(e)}\n{error_details}\n")
        except:
            pass
            
        # The task will be marked as FAILED and the exception will be stored in the result backend
        raise
