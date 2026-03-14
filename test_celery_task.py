from src.tasks.analysis_tasks import run_stock_analysis_task
from src.application.dto.analysis_dto import StockAnalysisRequest

request = StockAnalysisRequest(
    stock_code="600160",
    include_fundamental=True,
    include_technical=True,
    kline_limit=200,
    refine_roles=False,
)

task = run_stock_analysis_task.delay(request.model_dump())
print(f"Task submitted with ID: {task.id}")
