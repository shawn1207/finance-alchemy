"""CLI entry point for Finance Alchemy."""

import os
import typer
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables from .env
load_dotenv()

from rich.panel import Panel
from rich.table import Table

from ...application.dto.analysis_dto import StockAnalysisRequest
from ...application.use_cases.analyze_stock import AnalyzeStockUseCase

app = typer.Typer(
    name="finance-alchemy",
    help="Finance Alchemy — A股智能量化分析系统",
    add_completion=False,
)
console = Console()


@app.command()
def analyze(
    stock_code: str = typer.Argument(..., help="A股股票代码 (e.g. 000001)"),
    no_fundamental: bool = typer.Option(False, "--no-fundamental", help="跳过基本面分析"),
    no_technical: bool = typer.Option(False, "--no-technical", help="跳过技术面分析"),
    kline_limit: int = typer.Option(200, "--kline-limit", "-k", help="K线条数"),
    refine_roles: bool = typer.Option(False, "--refine-roles", "-r", help="使用大模型优化智能体角色"),
) -> None:
    """分析单只A股股票并生成交易策略报告。"""
    from pathlib import Path

    console.print(Panel(f"[bold cyan]Finance Alchemy — 开始分析: {stock_code}[/bold cyan]"))

    request = StockAnalysisRequest(
        stock_code=stock_code,
        include_fundamental=not no_fundamental,
        include_technical=not no_technical,
        kline_limit=kline_limit,
        refine_roles=refine_roles,
    )

    try:
        from ...config import get_settings
        from langchain_openai import ChatOpenAI

        settings = get_settings()
        # If the model name doesn't contain a slash, we assume it's an OpenAI model
        # unless it's a known non-OpenAI provider (handled by LiteLLM usually).
        # To be safe and flexible, we just use the model name from settings directly.
        model_name = settings.openai_model
        
        llm = ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )

        use_case = AnalyzeStockUseCase(llm=llm)
        result = use_case.execute(request)

        table = Table(title=f"股票 {stock_code} 分析结果", show_header=True)
        table.add_column("指标", style="cyan", width=16)
        table.add_column("值", style="bold green")

        s = result.strategy
        decision_color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(s.decision, "white")
        table.add_row("交易决策", f"[{decision_color}]{s.decision}[/{decision_color}]")
        table.add_row("置信度", f"{s.confidence:.1%}")
        table.add_row("建议仓位", f"{s.position_size_pct:.1f}%")
        table.add_row("止损", f"{s.stop_loss_pct:.1f}%")
        table.add_row("止盈", f"{s.take_profit_pct:.1f}%")
        table.add_row("风险等级", s.risk_level)
        table.add_row("耗时", f"{result.duration_seconds:.1f}s")

        console.print(table)
        console.print(Panel(s.rationale, title="[bold]策略详情[/bold]", border_style="blue"))

    except Exception as e:
        console.print(f"[bold red]分析失败: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def scan(
    codes: list[str] = typer.Argument(..., help="多个股票代码，空格分隔"),
    no_fundamental: bool = typer.Option(False, "--no-fundamental"),
    no_technical: bool = typer.Option(False, "--no-technical"),
) -> None:
    """批量扫描多支A股，输出汇总表格。"""
    results_table = Table(title="批量扫描结果")
    results_table.add_column("代码", style="cyan")
    results_table.add_column("决策", style="bold")
    results_table.add_column("置信度")
    results_table.add_column("风险")
    results_table.add_column("状态")

    for code in codes:
        console.rule(f"[cyan]分析 {code}")
        try:
            from ...config import get_settings
            from langchain_openai import ChatOpenAI

            settings = get_settings()
            llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
            request = StockAnalysisRequest(
                stock_code=code,
                include_fundamental=not no_fundamental,
                include_technical=not no_technical,
            )
            result = AnalyzeStockUseCase(llm=llm).execute(request)
            s = result.strategy
            color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(s.decision, "white")
            results_table.add_row(
                code,
                f"[{color}]{s.decision}[/{color}]",
                f"{s.confidence:.1%}",
                s.risk_level,
                "[green]完成[/green]",
            )
        except Exception as e:
            results_table.add_row(code, "-", "-", "-", f"[red]失败: {e}[/red]")

    console.print(results_table)


if __name__ == "__main__":
    app()

@app.command()
def gui():
    """Launch the Gradio GUI for stock analysis."""
    import os
    from pathlib import Path

    # Ensure the storage directory exists and is writable
    storage_path = Path("/tmp/finance_alchemy_storage")
    storage_path.mkdir(parents=True, exist_ok=True)
    os.environ["CREWAI_STORAGE_DIR"] = str(storage_path)

    from src.interface.gui.main import create_gradio_interface

    app = create_gradio_interface()
    app.launch(share=True)
