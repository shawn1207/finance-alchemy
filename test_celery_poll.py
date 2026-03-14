import time
from src.application.dto.analysis_dto import StockAnalysisRequest
from src.tasks.analysis_tasks import run_stock_analysis_task
from celery.result import AsyncResult

def main():
    request = StockAnalysisRequest(
        stock_code="600160",
        include_fundamental=True,
        include_technical=True,
        kline_limit=200,
        refine_roles=False,
    )

    print("Submitting task...")
    task = run_stock_analysis_task.delay(request.model_dump())
    task_id = task.id
    print(f"Task ID: {task_id}")

    task_result = AsyncResult(task_id)
    print("Polling task...")
    
    max_polls = 30
    polls = 0
    while not task_result.ready() and polls < max_polls:
        print(f"State: {task_result.state}")
        time.sleep(2)
        polls += 1

    print(f"Task finished with state: {task_result.state}")
    if task_result.successful():
        print("Success:", str(task_result.get())[:100] + "...")
    else:
        print("Error:", task_result.info)

if __name__ == "__main__":
    main()
    
